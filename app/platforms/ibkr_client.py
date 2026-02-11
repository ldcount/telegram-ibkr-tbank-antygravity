import logging
import requests
import xml.etree.ElementTree as ET
from app.config import Config

logger = logging.getLogger(__name__)


class IBKRClient:
    def __init__(self):
        self.token = Config.IBKR_FLEX_TOKEN
        self.query_id = Config.IBKR_QUERY_ID
        self.base_url = "https://www.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
        self.download_url = "https://www.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"

        if not self.token or not self.query_id:
            logger.warning("IBKR Flex credentials not set.")

    def get_portfolio_summary(self) -> dict:
        """
        Fetches the portfolio summary via Flex Query.
        Returns:
            {"total_usd": float, "error": str|None}
        """
        if not self.token or not self.query_id:
            return {"total_usd": 0.0}

        try:
            # Step 1: Request the report
            logger.info("Requesting IBKR Flex Report...")
            resp = requests.get(
                self.base_url,
                params={"t": self.token, "q": self.query_id, "v": "3"},
                timeout=10,
            )
            resp.raise_for_status()

            # Parse step 1 XML
            root = ET.fromstring(resp.content)

            status = root.find("Status")
            if status is not None and status.text == "Success":
                ref_code = root.find("ReferenceCode").text
                base_url = root.find("Url").text

                logger.info(
                    f"IBKR Report generated. Reference: {ref_code}. Downloading..."
                )

                # Step 2: Download the report
                dl_resp = requests.get(
                    base_url,
                    params={"t": self.token, "q": ref_code, "v": "3"},
                    timeout=30,
                )
                dl_resp.raise_for_status()

                # Parse step 2 XML (Actual Report)
                return self._parse_report(dl_resp.content)

            else:
                error_code = root.find("ErrorCode")
                error_msg = root.find("ErrorMessage")
                msg = f"IBKR Error {error_code.text if error_code is not None else '?'}: {error_msg.text if error_msg is not None else '?'}"
                logger.error(msg)
                return {"total_usd": 0.0, "error": msg}

        except Exception as e:
            logger.error(f"IBKR Flex Query Error: {e}")
            return {"total_usd": 0.0, "error": str(e)}

    def _parse_report(self, xml_content) -> dict:
        """
        Parses the Flex Query XML response.
        We look for 'NAV' or 'NetLiquidation' in 'AccountInformation' or 'EquitySummaryByReportDateInBase'.
        Expected structure (based on user XML):
        <FlexQueryResponse ...>
            <FlexStatements ...>
                <FlexStatement ...>
                    <EquitySummaryInBase>
                        <EquitySummaryByReportDateInBase total="236979.953968903" reportDate="09/02/2026"/>
                        <EquitySummaryByReportDateInBase total="236373.493968903" reportDate="10/02/2026"/>
                    </EquitySummaryInBase>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>
        """
        try:
            root = ET.fromstring(xml_content)

            flex_stmt = root.find(".//FlexStatement")
            if flex_stmt is None:
                return {"total_usd": 0.0, "error": "No FlexStatement found"}

            acc_info = flex_stmt.find(".//AccountInformation")
            equity_summary = flex_stmt.find(".//EquitySummaryInBase")

            nav = 0.0
            found = False

            # Strategy 1: Look for AccountInformation -> NetLiquidation (if present)
            if acc_info is not None:
                for attr in [
                    "netLiquidation",
                    "nav",
                    "totalNetAssetValue",
                    "equityWithLoanValue",
                ]:
                    if attr in acc_info.attrib:
                        nav = float(acc_info.attrib[attr])
                        found = True
                        break

            # Strategy 2: Look for EquitySummaryInBase -> EquitySummaryByReportDateInBase
            if not found and equity_summary is not None:
                # Find all children: EquitySummaryByReportDateInBase
                entries = equity_summary.findall(".//EquitySummaryByReportDateInBase")
                if entries:
                    # Sort by reportDate just in case (format usually DD/MM/YYYY or YYYYMMDD)
                    # Let's try to parse date or just take the last one as they are usually chronological
                    # simple last one strategy is best as it's the latest report generated
                    last_entry = entries[-1]

                    if "total" in last_entry.attrib:
                        nav = float(last_entry.attrib["total"])
                        found = True
                    elif "netLiquidation" in last_entry.attrib:
                        nav = float(last_entry.attrib["netLiquidation"])
                        found = True

            if not found:
                # Last resort: log all tags to help user debug
                # Collect tags from flex_stmt children
                tags_found = [elem.tag for elem in flex_stmt]
                logger.warning(
                    f"Could not find NAV in IBKR report. Tags in FlexStatement: {tags_found}"
                )
                if equity_summary is not None:
                    # Log attributes of EquitySummaryInBase itself? No, incorrect. Just log entries if any.
                    pass

                return {"total_usd": 0.0, "error": "NAV not found in report"}

            return {"total_usd": nav}

        except Exception as e:
            logger.error(f"Error parsing IBKR XML: {e}")
            return {"total_usd": 0.0, "error": f"Parse Error: {e}"}
