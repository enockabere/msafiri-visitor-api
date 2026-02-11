"""Traveler validation service for passport and age requirements."""
import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.travel_request import (
    TravelRequest, TravelRequestTraveler, TravelRequestDestination,
    TravelerType, DependantRelationship
)

logger = logging.getLogger(__name__)


class TravelerValidationService:
    """Service for validating traveler passport and age requirements."""

    def calculate_age_at_date(self, date_of_birth: date, reference_date: date) -> int:
        """
        Calculate age at a specific date.

        Args:
            date_of_birth: The person's date of birth
            reference_date: The date to calculate age at

        Returns:
            Age in years
        """
        age = reference_date.year - date_of_birth.year
        # Adjust if birthday hasn't occurred yet in reference year
        if (reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return age

    def get_earliest_departure_date(self, travel_request: TravelRequest) -> Optional[date]:
        """Get the earliest departure date from all destinations."""
        if not travel_request.destinations:
            return None

        departure_dates = [d.departure_date for d in travel_request.destinations if d.departure_date]
        if not departure_dates:
            return None

        return min(departure_dates)

    def validate_child_age(
        self,
        traveler: TravelRequestTraveler,
        earliest_departure: date
    ) -> Dict[str, Any]:
        """
        Validate that a child traveler is under 18 at time of travel.

        Args:
            traveler: The traveler to validate
            earliest_departure: Earliest departure date of the trip

        Returns:
            Dictionary with validation result:
            {
                "is_valid": bool,
                "age_at_travel": int or None,
                "error_message": str or None,
                "warning_message": str or None
            }
        """
        result = {
            "is_valid": True,
            "age_at_travel": None,
            "error_message": None,
            "warning_message": None
        }

        # Check if this is a child dependant
        is_child_dependant = (
            traveler.traveler_type == TravelerType.DEPENDANT and
            traveler.relation_type == DependantRelationship.CHILD.value
        )

        if not is_child_dependant:
            return result

        # Get date of birth from passport data
        dob = traveler.passport_date_of_birth
        if not dob:
            # Can't validate without DOB - will need passport upload
            return result

        # Calculate age at travel date
        age_at_travel = self.calculate_age_at_date(dob, earliest_departure)
        result["age_at_travel"] = age_at_travel

        if age_at_travel >= 18:
            result["is_valid"] = False
            result["error_message"] = (
                f"{traveler.traveler_name} will be {age_at_travel} years old at the time of travel. "
                f"Child dependants must be under 18. Please remove this traveler."
            )
        elif age_at_travel == 17:
            # Warning if child is close to turning 18
            result["warning_message"] = (
                f"{traveler.traveler_name} is currently 17 and may turn 18 before or during travel."
            )

        return result

    def validate_passport_requirements(
        self,
        db: Session,
        travel_request_id: int
    ) -> Dict[str, Any]:
        """
        Validate passport requirements for all travelers before submission.

        Args:
            db: Database session
            travel_request_id: ID of the travel request to validate

        Returns:
            Dictionary with validation results:
            {
                "can_submit": bool,
                "missing_child_passports": [traveler_ids],
                "age_warnings": [warning messages],
                "age_errors": [error messages],
                "travelers_to_remove": [traveler_ids]
            }
        """
        travel_request = db.query(TravelRequest).filter(
            TravelRequest.id == travel_request_id
        ).first()

        if not travel_request:
            return {
                "can_submit": False,
                "error": "Travel request not found"
            }

        result = {
            "can_submit": True,
            "missing_child_passports": [],
            "age_warnings": [],
            "age_errors": [],
            "travelers_to_remove": []
        }

        earliest_departure = self.get_earliest_departure_date(travel_request)
        if not earliest_departure:
            result["can_submit"] = False
            result["error"] = "No departure date found"
            return result

        for traveler in travel_request.travelers:
            # Check if this is a child dependant
            is_child_dependant = (
                traveler.traveler_type == TravelerType.DEPENDANT and
                traveler.relation_type == DependantRelationship.CHILD.value
            )

            if is_child_dependant:
                # Child dependants MUST have passport uploaded
                if not traveler.passport_file_url:
                    result["missing_child_passports"].append(traveler.id)
                    result["can_submit"] = False
                else:
                    # Validate age if we have DOB from passport
                    age_validation = self.validate_child_age(traveler, earliest_departure)

                    if not age_validation["is_valid"]:
                        result["age_errors"].append(age_validation["error_message"])
                        result["travelers_to_remove"].append(traveler.id)
                        result["can_submit"] = False

                    if age_validation["warning_message"]:
                        result["age_warnings"].append(age_validation["warning_message"])

        return result

    def is_passport_required(self, traveler: TravelRequestTraveler) -> bool:
        """
        Check if passport upload is required for this traveler.

        Child dependants require mandatory passport upload.
        Others can upload optionally.

        Args:
            traveler: The traveler to check

        Returns:
            True if passport is mandatory, False if optional
        """
        return (
            traveler.traveler_type == TravelerType.DEPENDANT and
            traveler.relation_type == DependantRelationship.CHILD.value
        )

    def calculate_is_child_under_18(
        self,
        date_of_birth: date,
        reference_date: Optional[date] = None
    ) -> bool:
        """
        Calculate if someone is under 18 at a given date.

        Args:
            date_of_birth: The person's date of birth
            reference_date: Date to check against (defaults to today)

        Returns:
            True if under 18, False otherwise
        """
        if not reference_date:
            reference_date = date.today()

        age = self.calculate_age_at_date(date_of_birth, reference_date)
        return age < 18


# Singleton instance
traveler_validation_service = TravelerValidationService()
