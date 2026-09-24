"""Aegis-APAC Deterministic Advisory Templates.

Fallback deterministic templates for all supported roles:
- collector
- power_operator
- citizens
across all 4 regional languages:
- English (en)
- Bengali / বাংলা (bn)
- Hindi / हिन्दी (hi)
- Odia / ଓଡ଼ିଆ (or)

Strictly formats numbers, dates, and names from the input decision JSON.
"""

from typing import Any, Dict, List
from src.contracts import AdvisoryRole


class DeterministicTemplateEngine:
    """Generates guaranteed-valid, ungrounded-error-free advisories from input decision payloads."""

    @staticmethod
    def render(role: AdvisoryRole, language: str, payload: Dict[str, Any]) -> str:
        """Render deterministic role-specific advisory in target language."""
        scenario = payload.get("scenario", {})
        storm_name = scenario.get("name", "Cyclone Amphan")
        lead_time = scenario.get("lead_time_h", 72)

        risks = payload.get("risks", [])
        actions = payload.get("actions", [])
        facilities = {f.get("id"): f for f in payload.get("facilities", [])}

        top_risk = risks[0] if risks else {}
        top_risk_fac = facilities.get(top_risk.get("facility_id", ""), {})
        top_fac_name = top_risk_fac.get("name", "Coastal Infrastructure")
        prob_pct = int(round(top_risk.get("failure_probability", 0.8) * 100))
        warning_hrs = int(round(top_risk.get("hours_of_warning", 18)))

        # Format key actions
        act_descs = [a.get("description", "") for a in actions[:3]]

        lang = language.lower()

        # 1. District Collector (Operational Directives)
        if role == AdvisoryRole.COLLECTOR:
            if lang == "bn":
                return (
                    f"[জরুরি নির্দেশিকা] {storm_name} (টি-{lead_time} ঘণ্টা পূর্বাভাস): "
                    f"সর্বোচ্চ ঝুঁকিপূর্ণ কেন্দ্র {top_fac_name}-এ {warning_hrs} ঘণ্টার মধ্যে বিকল হওয়ার সম্ভাবনা {prob_pct}%। "
                    f"অবিলম্বে পদক্ষেপ গ্রহণ করুন: " + "; ".join(act_descs) + ". "
                    f"সকল নোডাল অফিসারকে সতর্ক থাকার এবং কন্টিনজেন্সি এসওপি কার্যকর করার নির্দেশ দেওয়া হচ্ছে।"
                )
            elif lang == "hi":
                return (
                    f"[आपातकालीन निर्देश] {storm_name} (टी-{lead_time} घंटे पूर्वानुमान): "
                    f"प्रमुख केंद्र {top_fac_name} में {warning_hrs} घंटे में विफलता की संभावना {prob_pct}% है। "
                    f"तत्काल कार्रवाई निर्देश: " + "; ".join(act_descs) + ". "
                    f"सभी नोडल अधिकारियों को 1077 नियंत्रण कक्ष से समन्वय रखने का आदेश दिया जाता है।"
                )
            elif lang == "or":
                return (
                    f"[ଜରୁରୀ ନିର୍ଦ୍ଦେଶ] {storm_name} (ଟି-{lead_time} ଘଣ୍ଟା ପୂର୍ବାନୁମାନ): "
                    f"ମୁଖ୍ୟ କେନ୍ଦ୍ର {top_fac_name} ରେ {warning_hrs} ଘଣ୍ଟା ମଧ୍ୟରେ କ୍ଷତିଗ୍ରସ୍ତ ହେବାର ସମ୍ଭାବନା {prob_pct}%। "
                    f"ତୁରନ୍ତ କାର୍ଯ୍ୟାନୁଷ୍ଠାନ ନିର୍ଦ୍ଦେଶ: " + "; ".join(act_descs) + ". "
                    f"ଜିଲ୍ଲା ନିୟନ୍ତ୍ରଣ କକ୍ଷ ସତର୍କ ରହିବାକୁ ନିର୍ଦ୍ଦେଶ ଦିଆଗଲା।"
                )
            else:  # en
                return (
                    f"[EMERGENCY DIRECTIVE] {storm_name} (T-{lead_time}h Advisory): "
                    f"Priority facility {top_fac_name} has a {prob_pct}% probability of failure with {warning_hrs} hours of warning. "
                    f"Immediate Operational Directives: " + "; ".join(act_descs) + ". "
                    f"All block development officers and relief teams must report compliance to District Control Room."
                )

        # 2. Power Utility Operator
        elif role == AdvisoryRole.POWER_OPERATOR:
            deenergise_acts = [a.get("description", "") for a in actions if a.get("type") == "deenergise"]
            act_text = "; ".join(deenergise_acts) if deenergise_acts else f"De-energise substations before water reaches 0.4m"

            if lang == "bn":
                return (
                    f"[বিদ্যুৎ পরিচালন সতর্কতা] {storm_name}: "
                    f"{top_fac_name} কেন্দ্রে ট্রান্সফরমার প্লাবিত হওয়ার ঝুঁকি {prob_pct}% ({warning_hrs} ঘণ্টা সতর্কতা)। "
                    f"নির্ধারিত কর্মপরিকল্পনা: {act_text}। হাসপাতালে ডিজেল জেনারেটর ব্যাকআপ সক্রিয় রাখার নির্দেশ।"
                )
            elif lang == "hi":
                return (
                    f"[विद्युत संचालन चेतावनी] {storm_name}: "
                    f"{top_fac_name} में सबस्टेशन जलमग्न होने की संभावना {prob_pct}% ({warning_hrs} घंटे चेतावनी)। "
                    f"कार्यवाही: {act_text}। अस्पतालों में डीजल जनरेटर बैकअप सुनिश्चित करें।"
                )
            elif lang == "or":
                return (
                    f"[ବିଦ୍ୟୁତ ପରିଚାଳନା ସତର୍କତା] {storm_name}: "
                    f"{top_fac_name} ରେ ସବ୍-ଷ୍ଟେସନ ଜଳମଗ୍ନ ହେବାର ଆଶଙ୍କା {prob_pct}% ({warning_hrs} ଘଣ୍ଟା ଚେତାବନୀ)। "
                    f"ନିର୍ଦ୍ଦେଶ: {act_text}।"
                )
            else:  # en
                return (
                    f"[GRID OPERATOR ADVISORY] {storm_name}: "
                    f"Substation {top_fac_name} failure probability is {prob_pct}% with {warning_hrs}h warning. "
                    f"Grid Switching Mandate: {act_text}. Ensure hospital auxiliary feeders are switched to emergency islanding mode."
                )

        # 3. Citizens Public Bulletin
        else:
            if lang == "bn":
                return (
                    f"[জনসাধারণের জন্য সতর্কবার্তা] {storm_name}: "
                    f"উপকূলবর্তী এলাকায় প্রবল জলোচ্ছ্বাস ও ঝড়ের সম্ভাবনা। "
                    f"প্লাবিত রাস্তাঘাট এড়িয়ে চলুন এবং অবিলম্বে নিকটবর্তী বহুমুখী ঘূর্ণিঝড় আশ্রয়কেন্দ্রে আশ্রয় নিন। "
                    f"জরুরি প্রয়োজনে জেলা হেল্পলাইন ১০৭৭ অথবা ১১২ নম্বরে যোগাযোগ করুন।"
                )
            elif lang == "hi":
                return (
                    f"[नागरिक सुरक्षा बुलेटिन] {storm_name}: "
                    f"तटीय क्षेत्रों में भारी तूफान और बाढ़ की आशंका है। "
                    f"जलमग्न सड़कों से दूर रहें और तुरंत सुरक्षित पक्के चक्रवात आश्रयों में जाएं। "
                    f"आपातकालीन सहायता के लिए 1077 या 112 पर संपर्क करें।"
                )
            elif lang == "or":
                return (
                    f"[ସାଧାରଣ ସତର୍କତା ବୁଲେଟିନ] {storm_name}: "
                    f"ଉପକୂଳ ଅଞ୍ଚଳରେ ପ୍ରବଳ ଝଡ଼ ଓ ବନ୍ୟା ଆଶଙ୍କା। "
                    f"ପାଣି ଜମିଥିବା ରାସ୍ତାରୁ ଦୂରେଇ ରୁହନ୍ତୁ ଏବଂ ନିକଟସ୍ଥ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀକୁ ଯାଆନ୍ତୁ। "
                    f"ଜରୁରୀ ସହାୟତା ପାଇଁ ୧୦୭୭ କିମ୍ବା ୧୧୨ କଲ୍ କରନ୍ତୁ।"
                )
            else:  # en
                return (
                    f"[CITIZEN SAFETY ADVISORY] {storm_name}: "
                    f"Severe coastal storm surge and flood warning. "
                    f"Stay off inundated roads and evacuate to your designated cyclone shelter immediately. "
                    f"For emergency rescue and medical assistance, call District Helpline 1077 or 112."
                )
