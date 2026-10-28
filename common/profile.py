"""Loads and validates the applicant profile from profile.yaml."""
import yaml
from pathlib import Path


class Profile:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def load(cls, path: str = "profile.yaml") -> "Profile":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"{path} not found. Copy profile.yaml and fill in your real details first."
            )
        with p.open() as f:
            data = yaml.safe_load(f)
        cls._validate(data)
        return cls(data)

    @staticmethod
    def _validate(data: dict):
        required_blocking = [
            "total_experience_years",
            "notice_period_days",
            "current_ctc_lpa",
            "expected_ctc_lpa",
            "resume_file_name",
        ]
        missing = [k for k in required_blocking if data.get(k) in (None, "")]
        if missing:
            raise ValueError(
                "profile.yaml is missing required fields before this can run safely: "
                + ", ".join(missing)
                + ". These gate real screening questions — fill them in with your real numbers."
            )

    def __getattr__(self, item):
        if item in self.data:
            return self.data[item]
        raise AttributeError(item)

    def answer_library(self) -> dict:
        """Common recurring screening-question answers, pre-computed once."""
        d = self.data

        if d.get("immediately_available"):
            notice_period = "Immediately available"
        else:
            notice_period = f"{d.get('notice_period_days', 0)} days"

        if d.get("ctc_disclosure_policy") == "negotiable":
            current_ctc = "Prefer to discuss"
        else:
            current_ctc = f"{d.get('current_ctc_lpa', 0)} LPA"

        if d.get("expected_ctc_text"):
            expected_ctc = str(d.get("expected_ctc_text"))
        elif d.get("ctc_disclosure_policy") == "negotiable":
            expected_ctc = "Negotiable"
        else:
            expected_ctc = f"{d.get('expected_ctc_lpa', 6)} LPA"

        return {
            "years_experience": str(d.get("total_experience_years", 0)),
            "notice_period": notice_period,
            "current_ctc": current_ctc,
            "expected_ctc": expected_ctc,
            "current_city": str(d.get("current_city", "")),
            "relocate": "Yes" if d.get("relocate_cities") else "No",
            "night_shift": "Yes" if d.get("night_shift_ok") else "No",
            "weekend_work": "Yes" if d.get("weekend_ok") else "No",
            "candidate_name": str(d.get("candidate_name", "")),
            "email": str(d.get("email", "")),
            "phone": str(d.get("phone", "")),
            "highest_qualification": str(d.get("highest_qualification", "")),
            "college": str(d.get("college", "")),
            "degree": str(d.get("degree", "")),
            "cgpa": str(d.get("cgpa", "")),
            "linkedin": str(d.get("linkedin_url", "")),
            "github": str(d.get("github_url", "")),
        }

