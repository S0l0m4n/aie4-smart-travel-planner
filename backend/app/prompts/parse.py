PARSE_SYSTEM_PROMPT = """
The user will describe their ideal trip. Decide on how to judge the following
features based on the their description:
1. **hiking_score** (1–10): quality and quantity of hiking, trekking, and trail-based outdoor activities
2. **beach_score** (1–10): quality, quantity, and accessibility of beaches
3. **cultural_sites_score** (1–10): museums, historical landmarks, architecture, local traditions and heritage
4. **nightlife_score** (1–10): bars, clubs, live music, entertainment scene
5. **family_friendly_score** (1–10): kid-oriented attractions, ease of travel with children, general safety for families
6. **luxury_infrastructure_score** (1–10): high-end hotels, fine dining, spas, exclusive experiences
7. **avg_accom_cost** (amount in USD):  average nightly accommodation cost, mid-range
8. **avg_daily_expense** (amount in USD): food, transport, activities per day, excluding accommodation
9. **safety_score** (1–10): personal safety for tourists, low crime, political stability
10. **remoteness_score** (1–10): how off-the-beaten-path it is, inverse of mass tourism volume

Each feature is scored between 1 to 10, except for the two cost features, which
represent an average amount per day.
"""
