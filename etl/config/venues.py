"""Venue identity policy.

The Cricsheet data uses 60 distinct venue strings for ~36 physical grounds. The
variation is of two kinds:

  * Pure formatting / suffix noise:
    "Eden Gardens" vs "Eden Gardens, Kolkata";
    "MA Chidambaram Stadium" vs ", Chepauk" vs ", Chepauk, Chennai".
  * Physical grounds that were renamed, which we MERGE to one venue under the
    current name (the same seats, a comprehensive DB should not split them):
    Feroz Shah Kotla -> Arun Jaitley Stadium (Delhi),
    Sardar Patel Stadium, Motera -> Narendra Modi Stadium (Ahmedabad),
    Subrata Roy Sahara Stadium -> Maharashtra Cricket Association Stadium (Pune),
    "Punjab Cricket Association Stadium, Mohali" -> PCA IS Bindra Stadium,
    Sheikh Zayed Stadium -> Zayed Cricket Stadium (Abu Dhabi).

Each canonical venue carries a stable ``venue_id`` slug, a display name, a city,
and the list of raw strings that map to it. City is fixed here because the raw
``city`` field is missing for 51 matches and is occasionally inconsistent
(e.g. "Navi Mumbai" vs "Mumbai" for the same DY Patil ground).
"""

# venue_id, display name, city, [raw variants]
VENUES = [
    ("delhi_kotla",        "Arun Jaitley Stadium", "Delhi",
        ["Arun Jaitley Stadium", "Arun Jaitley Stadium, Delhi", "Feroz Shah Kotla"]),
    ("cuttack_barabati",   "Barabati Stadium", "Cuttack",
        ["Barabati Stadium"]),
    ("guwahati_barsapara", "Barsapara Cricket Stadium", "Guwahati",
        ["Barsapara Cricket Stadium, Guwahati"]),
    ("lucknow_ekana",      "Ekana Cricket Stadium", "Lucknow",
        ["Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"]),
    ("mumbai_brabourne",   "Brabourne Stadium", "Mumbai",
        ["Brabourne Stadium", "Brabourne Stadium, Mumbai"]),
    ("eastlondon_buffalo", "Buffalo Park", "East London",
        ["Buffalo Park"]),
    ("kimberley_debeers",  "De Beers Diamond Oval", "Kimberley",
        ["De Beers Diamond Oval"]),
    ("navimumbai_dypatil", "Dr DY Patil Sports Academy", "Navi Mumbai",
        ["Dr DY Patil Sports Academy", "Dr DY Patil Sports Academy, Mumbai"]),
    ("vizag_acavdca",      "ACA-VDCA Cricket Stadium", "Visakhapatnam",
        ["Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
         "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam"]),
    ("dubai_intl",         "Dubai International Cricket Stadium", "Dubai",
        ["Dubai International Cricket Stadium"]),
    ("kolkata_eden",       "Eden Gardens", "Kolkata",
        ["Eden Gardens", "Eden Gardens, Kolkata"]),
    ("kanpur_greenpark",   "Green Park", "Kanpur",
        ["Green Park"]),
    ("dharamsala_hpca",    "Himachal Pradesh Cricket Association Stadium", "Dharamsala",
        ["Himachal Pradesh Cricket Association Stadium",
         "Himachal Pradesh Cricket Association Stadium, Dharamsala"]),
    ("indore_holkar",      "Holkar Cricket Stadium", "Indore",
        ["Holkar Cricket Stadium"]),
    ("ranchi_jsca",        "JSCA International Stadium Complex", "Ranchi",
        ["JSCA International Stadium Complex"]),
    ("durban_kingsmead",   "Kingsmead", "Durban",
        ["Kingsmead"]),
    ("bengaluru_chinnaswamy", "M Chinnaswamy Stadium", "Bengaluru",
        ["M Chinnaswamy Stadium", "M Chinnaswamy Stadium, Bengaluru", "M.Chinnaswamy Stadium"]),
    ("chennai_chepauk",    "MA Chidambaram Stadium", "Chennai",
        ["MA Chidambaram Stadium", "MA Chidambaram Stadium, Chepauk",
         "MA Chidambaram Stadium, Chepauk, Chennai"]),
    ("mullanpur_maharaja", "Maharaja Yadavindra Singh International Cricket Stadium", "New Chandigarh",
        ["Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur",
         "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh"]),
    ("pune_mca",           "Maharashtra Cricket Association Stadium", "Pune",
        ["Maharashtra Cricket Association Stadium",
         "Maharashtra Cricket Association Stadium, Pune", "Subrata Roy Sahara Stadium"]),
    ("ahmedabad_narendramodi", "Narendra Modi Stadium", "Ahmedabad",
        ["Narendra Modi Stadium, Ahmedabad", "Sardar Patel Stadium, Motera"]),
    ("kochi_nehru",        "Nehru Stadium", "Kochi",
        ["Nehru Stadium"]),
    ("johannesburg_wanderers", "New Wanderers Stadium", "Johannesburg",
        ["New Wanderers Stadium"]),
    ("capetown_newlands",  "Newlands", "Cape Town",
        ["Newlands"]),
    ("bloemfontein_outsurance", "OUTsurance Oval", "Bloemfontein",
        ["OUTsurance Oval"]),
    ("mohali_pca",         "Punjab Cricket Association IS Bindra Stadium", "Mohali",
        ["Punjab Cricket Association IS Bindra Stadium",
         "Punjab Cricket Association IS Bindra Stadium, Mohali",
         "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh",
         "Punjab Cricket Association Stadium, Mohali"]),
    ("hyderabad_rajivgandhi", "Rajiv Gandhi International Stadium", "Hyderabad",
        ["Rajiv Gandhi International Stadium", "Rajiv Gandhi International Stadium, Uppal",
         "Rajiv Gandhi International Stadium, Uppal, Hyderabad"]),
    ("rajkot_saurashtra",  "Saurashtra Cricket Association Stadium", "Rajkot",
        ["Saurashtra Cricket Association Stadium"]),
    ("jaipur_sawaimansingh", "Sawai Mansingh Stadium", "Jaipur",
        ["Sawai Mansingh Stadium", "Sawai Mansingh Stadium, Jaipur"]),
    ("raipur_vnsingh",     "Shaheed Veer Narayan Singh International Stadium", "Raipur",
        ["Shaheed Veer Narayan Singh International Stadium",
         "Shaheed Veer Narayan Singh International Stadium, Raipur"]),
    ("sharjah",            "Sharjah Cricket Stadium", "Sharjah",
        ["Sharjah Cricket Stadium"]),
    ("abudhabi_zayed",     "Zayed Cricket Stadium", "Abu Dhabi",
        ["Sheikh Zayed Stadium", "Zayed Cricket Stadium, Abu Dhabi"]),
    ("portelizabeth_stgeorges", "St George's Park", "Port Elizabeth",
        ["St George's Park"]),
    ("centurion_supersport", "SuperSport Park", "Centurion",
        ["SuperSport Park"]),
    ("nagpur_vca",         "Vidarbha Cricket Association Stadium", "Nagpur",
        ["Vidarbha Cricket Association Stadium, Jamtha"]),
    ("mumbai_wankhede",    "Wankhede Stadium", "Mumbai",
        ["Wankhede Stadium", "Wankhede Stadium, Mumbai"]),
]

# raw venue string -> (venue_id, display name, city)
_RAW_TO_VENUE = {
    raw: (vid, name, city)
    for vid, name, city, variants in VENUES
    for raw in variants
}


def resolve_venue(raw_venue: str):
    """Return (venue_id, display_name, city) for a raw venue string."""
    try:
        return _RAW_TO_VENUE[raw_venue]
    except KeyError:
        raise KeyError(
            f"Unknown venue {raw_venue!r}. Add it to etl/config/venues.py."
        )
