from typing import NotRequired, TypedDict


class DiscogsReleaseArtist(TypedDict):
    anv: str
    id: int
    join: str
    name: str
    resource_url: str
    role: str
    tracks: str

class DiscogsReleaseExtraArtist(TypedDict):
    any: str
    id: int
    join: str
    name: str
    resource_url: str
    role: str
    tracks: str

class DiscogsContributor(TypedDict):
    resource_url: str
    username: str

class DiscogsRating(TypedDict):
    average: int
    count: int

class DiscogsCompany(TypedDict):
    catno: str
    entity_type: str
    entity_type_name: str
    id: int
    name: str
    resource_url: str

class DicogsReleaseCommunity(TypedDict):
    contributors: list[DiscogsContributor]
    data_quality: str
    have: int
    want: int
    rating: DiscogsRating
    status: str
    submitter: DiscogsContributor

class DiscogsFormat(TypedDict):
    descriptions: list[str]
    name: str
    qty: str
    text: NotRequired[str]

class DiscogsIdentifier(TypedDict):
    type: str
    value: str

class DiscogsImage(TypedDict):
    height: int
    resource_url: str
    type: str
    uri: str
    uri150: str
    width: int

class DiscogsLabel(TypedDict):
    catno: str
    entity_type: str
    id: int
    name: str
    resource_url: str

class DiscogsTrack(TypedDict):
    duration: str
    position: str
    title: str
    type_: str
    artists: NotRequired[list[DiscogsReleaseArtist]]
    extraartists: NotRequired[list[DiscogsReleaseArtist]]

class DiscogsVideo(TypedDict):
    description: str
    duration: str
    embed: bool
    title: str
    uri: str

class DiscogsRelease(TypedDict):
    title: str
    id: int
    artists: list[DiscogsReleaseArtist]
    thumb: str
    community: DicogsReleaseCommunity
    companies: list[DiscogsCompany]
    country: str
    date_added: str
    date_changed: str
    estimated_weight: int
    extraartists:  list[DiscogsReleaseArtist]
    format_quantity: int
    formats: list[DiscogsFormat]
    genres: list[str]
    identifiers: list[DiscogsIdentifier]
    images: list[DiscogsImage]
    labels: list[DiscogsLabel]
    lowest_price: float
    master_id: int
    master_url: int
    notes: str
    num_for_sale: int
    released: str
    released_formatted: str
    resource_url: str
    series: list[str]
    status: str
    styles: list[str]
    tracklist: list[DiscogsTrack]
    uri: str
    videos: list[DiscogsVideo]
    year: int

DISCOGS_ISO_COUNTRY_MAPPING = {
    "": [],
    "Australia": ["AU"],
    "Belgium": ["BE"],
    "Brazil": ["BR"],
    "Canada": ["CA"],
    "China": ["CN"],
    "Cuba": ["CU"],
    "France": ["FR"],
    "Germany": ["DE"],
    "Italy": ["IT"],
    "Ireland": ["IE"],
    "India": ["IN"],
    "Jamaica": ["JM"],
    "Japan": ["JP"],
    "Mexico": ["MX"],
    "Netherlands": ["NL"],
    "New Zealand": ["NZ"],
    "Spain": ["ES"],
    "Sweden": ["SE"],
    "Switzerland": ["CH"],
    "UK": ["GB"],
    "US": ["US"],
    "Africa": [],
    "Asia": [],
    "Australia & New Zealand": ["AU", "NZ"],
    "Benelux": ["BE", "NL", "LU"],
    "Australasia": ["AU", "NZ"],
    "Central America": [],
    "Czech Republic & Slovakia": ["CZ", "SK"],
    "Czech And Slovak Federative Republic": ["XC"],
    "Europe": ["XE"],
    "Gulf Cooperation Council": ["BH", "KW", "OM", "QA", "SA", "AE"],
    "Germany, Austria, & Switzerland": ["DE", "AT", "CH"],
    "Germany & Switzerland": ["DE", "CH"],
    "France & Benelux": ["FR", "BE", "NL", "LU"],
    "Middle East": [],
    "North America (inc Mexico)": ["CA", "MX", "US"],
    "North & South America": [],
    "South America": [],
    "Scandinavia": ["DK", "NO", "SE"],
    "South East Asia": [],
    "UK & Ireland": ["GB", "IE"],
    "UK, Europe & US": ["GB", "XE", "US"],
    "UK & Europe": ["GB", "XE"],
    "UK & US": ["GB", "US"],
    "UK & France": ["GB", "FR"],
    "UK, Europe & Japan": ["GB", "XE", "JP"],
    "UK, Europe & Israel": ["GB", "XE", "IL"],
    "UK & Germany": ["GB", "DE"],
    "USA & Canada": ["US", "CA"],
    "USA, Canada & UK": ["US", "CA", "GB"],
    "USA, Canada & Europe": ["US", "CA", "XE"],
    "USA & Europe": ["US", "XE"],
    "Worldwide": ["XW"],
    "Afghanistan": ["AF"],
    "Abkhazia": ["GE"],
    "Albania": ["AL"],
    "Algeria": ["DZ"],
    "American Samoa": ["AS"],
    "Andorra": ["AD"],
    "Angola": ["AO"],
    "Anguilla": ["AI"],
    "Antarctica": ["AQ"],
    "Antigua & Barbuda": ["AG"],
    "Argentina": ["AR"],
    "Armenia": ["AM"],
    "Aruba": ["AW"],
    "Austria": ["AT"],
    "Austria-Hungary": ["AT", "HU"],
    "Azerbaijan": ["AZ"],
    "Bahamas, The": ["BS"],
    "Bahrain": ["BH"],
    "Bangladesh": ["BD"],
    "Barbados": ["BB"],
    "Belarus": ["BY"],
    "Belize": ["BZ"],
    "Belgian Congo": ["CD"],
    "Benin": ["BJ"],
    "Bermuda": ["BM"],
    "Bhutan": ["BT"],
    "Bolivia": ["BO"],
    "Bohemia": ["CZ"],
    "Bosnia & Herzegovina": ["BA"],
    "Botswana": ["BW"],
    "British Indian Ocean Territory": ["IO"],
    "British Virgin Islands": ["VG"],
    "Brunei": ["BN"],
    "Bulgaria": ["BG"],
    "Burkina Faso": ["BF"],
    "Burma": ["MM"],
    "Burundi": ["BI"],
    "Cambodia": ["KH"],
    "Cameroon": ["CM"],
    "Cape Verde": ["CV"],
    "Cayman Islands": ["KY"],
    "Central African Republic": ["CF"],
    "Chad": ["TD"],
    "Chile": ["CL"],
    "Christmas Island": ["CX"],
    "Cocos (Keeling) Islands": ["CC"],
    "Colombia": ["CO"],
    "Comoros": ["KM"],
    "Congo, Democratic Republic of the": ["CD"],
    "Congo, Republic of the": ["CG"],
    "Cook Islands": ["CK"],
    "Costa Rica": ["CR"],
    "Croatia": ["HR"],
    "Curaçao": ["CW"],
    "Cyprus": ["CY"],
    "Czech Republic": ["CZ"],
    "Czechoslovakia": ["XC"],
    "Denmark": ["DK"],
    "Dahomey": ["BJ"],
    "Djibouti": ["DJ"],
    "Dominica": ["DM"],
    "Dominican Republic": ["DO"],
    "Dutch East Indies": ["ID"],
    "East Timor": ["TL"],
    "Ecuador": ["EC"],
    "Egypt": ["EG"],
    "El Salvador": ["SV"],
    "Equatorial Guinea": ["GQ"],
    "Eritrea": ["ER"],
    "Estonia": ["EE"],
    "Ethiopia": ["ET"],
    "Falkland Islands": ["FK"],
    "Faroe Islands": ["FO"],
    "Fiji": ["FJ"],
    "Finland": ["FI"],
    "French Guiana": ["GF"],
    "French Polynesia": ["PF"],
    "French Southern & Antarctic Lands": ["TF"],
    "Gabon": ["GA"],
    "Gambia, The": ["GM"],
    "Gaza Strip": ["PS"],
    "Georgia": ["GE"],
    "German Democratic Republic (GDR)": ["XG"],
    "Ghana": ["GH"],
    "Gibraltar": ["GI"],
    "Greece": ["GR"],
    "Greenland": ["GL"],
    "Grenada": ["GD"],
    "Guadeloupe": ["GP"],
    "Guam": ["GU"],
    "Guatemala": ["GT"],
    "Guernsey": ["GG"],
    "Guinea": ["GN"],
    "Guinea-Bissau": ["GW"],
    "Guyana": ["GY"],
    "Haiti": ["HT"],
    "Honduras": ["HN"],
    "Hong Kong": ["HK"],
    "Hong Kong & Thailand": ["HK", "TH"],
    "Hungary": ["HU"],
    "Iceland": ["IS"],
    "Indochina": ["VN", "LA", "KH"],
    "Indonesia": ["ID"],
    "Iran": ["IR"],
    "Iraq": ["IQ"],
    "Israel": ["IL"],
    "Ivory Coast": ["CI"],
    "Isle Of Man": ["IM"],
    "Italian East Africa": ["ET", "ER", "SO"],
    "Jersey": ["JE"],
    "Jordan": ["JO"],
    "Kazakhstan": ["KZ"],
    "Kenya": ["KE"],
    "Kiribati": ["KI"],
    "Korea (pre-1945)": ["KR", "KP"],
    "Kuwait": ["KW"],
    "Kosovo": ["XK"],
    "Kyrgyzstan": ["KG"],
    "Laos": ["LA"],
    "Latvia": ["LV"],
    "Lebanon": ["LB"],
    "Lesotho": ["LS"],
    "Liberia": ["LR"],
    "Libya": ["LY"],
    "Liechtenstein": ["LI"],
    "Lithuania": ["LT"],
    "Luxembourg": ["LU"],
    "Macau": ["MO"],
    "Macedonia": ["MK"],
    "Madagascar": ["MG"],
    "Malawi": ["MW"],
    "Malaysia": ["MY"],
    "Maldives": ["MV"],
    "Mali": ["ML"],
    "Malta": ["MT"],
    "Marshall Islands": ["MH"],
    "Martinique": ["MQ"],
    "Mauritania": ["MR"],
    "Mauritius": ["MU"],
    "Mayotte": ["YT"],
    "Micronesia, Federated States of": ["FM"],
    "Moldova, Republic of": ["MD"],
    "Monaco": ["MC"],
    "Mongolia": ["MN"],
    "Montserrat": ["MS"],
    "Montenegro": ["ME"],
    "Morocco": ["MA"],
    "Mozambique": ["MZ"],
    "Namibia": ["NA"],
    "Nauru": ["NR"],
    "Nepal": ["NP"],
    "Netherlands Antilles": ["AN"],
    "New Caledonia": ["NC"],
    "Nicaragua": ["NI"],
    "Niger": ["NE"],
    "Nigeria": ["NG"],
    "Niue": ["NU"],
    "Norfolk Island": ["NF"],
    "Northern Mariana Islands": ["MP"],
    "North Korea": ["KP"],
    "Norway": ["NO"],
    "Oman": ["OM"],
    "Ottoman Empire": ["TR"],
    "Pakistan": ["PK"],
    "Palau": ["PW"],
    "Palestine": ["PS"],
    "Panama": ["PA"],
    "Papua New Guinea": ["PG"],
    "Paraguay": ["PY"],
    "Peru": ["PE"],
    "Philippines": ["PH"],
    "Pitcairn Islands": ["PN"],
    "Poland": ["PL"],
    "Portugal": ["PT"],
    "Protectorate of Bohemia and Moravia": ["CZ"],
    "Puerto Rico": ["PR"],
    "Qatar": ["QA"],
    "Reunion": ["RE"],
    "Romania": ["RO"],
    "Rhodesia": ["ZW"],
    "Russia": ["RU"],
    "Russia & CIS": ["RU"],
    "Rwanda": ["RW"],
    "Saint Helena": ["SH"],
    "Saar": ["DE"],
    "Saint Kitts and Nevis": ["KN"],
    "Saint Lucia": ["LC"],
    "Saint Pierre and Miquelon": ["PM"],
    "Saint Vincent and the Grenadines": ["VC"],
    "Samoa": ["WS"],
    "San Marino": ["SM"],
    "Sao Tome and Principe": ["ST"],
    "Saudi Arabia": ["SA"],
    "Senegal": ["SN"],
    "Serbia and Montenegro": ["CS"],
    "Serbia": ["RS"],
    "Seychelles": ["SC"],
    "Sierra Leone": ["SL"],
    "Singapore": ["SG"],
    "Sint Maarten": ["SX"],
    "Singapore, Malaysia & Hong Kong": ["SG", "MY", "HK"],
    "Singapore & Malaysia": ["SG", "MY"],
    "Singapore, Malaysia, Hong Kong & Thailand": ["SG", "MY", "HK", "TH"],
    "Slovakia": ["SK"],
    "Slovenia": ["SI"],
    "Solomon Islands": ["SB"],
    "Somalia": ["SO"],
    "Southern Rhodesia": ["ZW"],
    "South Africa": ["ZA"],
    "South Georgia and the South Sandwich Islands": ["GS"],
    "South Korea": ["KR"],
    "South Vietnam": ["VN"],
    "South Pacific": [],
    "South West Africa": ["NA"],
    "Southern Sudan": ["SS"],
    "Sri Lanka": ["LK"],
    "Sudan": ["SD"],
    "Suriname": ["SR"],
    "Swaziland": ["SZ"],
    "Syria": ["SY"],
    "Taiwan": ["TW"],
    "Tajikistan": ["TJ"],
    "Tanzania": ["TZ"],
    "Thailand": ["TH"],
    "Togo": ["TG"],
    "Tibet": ["CN"],
    "Tokelau": ["TK"],
    "Tonga": ["TO"],
    "Trinidad & Tobago": ["TT"],
    "Tunisia": ["TN"],
    "Turkey": ["TR"],
    "Turkmenistan": ["TM"],
    "Turks and Caicos Islands": ["TC"],
    "Tuvalu": ["TV"],
    "Uganda": ["UG"],
    "Ukraine": ["UA"],
    "United Arab Emirates": ["AE"],
    "Upper Volta": ["BF"],
    "Uruguay": ["UY"],
    "USSR": ["SU"],
    "Uzbekistan": ["UZ"],
    "Vanuatu": ["VU"],
    "Vatican City": ["VA"],
    "Venezuela": ["VE"],
    "Vietnam": ["VN"],
    "Virgin Islands": ["VI"],
    "Wake Island": ["UM"],
    "Wallis and Futuna": ["WF"],
    "West Bank": ["PS"],
    "Western Sahara": ["EH"],
    "Yemen": ["YE"],
    "Yugoslavia": ["YU"],
    "Zambia": ["ZM"],
    "Zaire": ["CD"],
    "Zanzibar": ["TZ"],
    "Zimbabwe": ["ZW"],
}

# Follows a pattern of Discogs Major Format -> Discogs Description -> MusicBrainz Format
DISCOGS_FORMAT_MAPPING = {
    "Vinyl": {
        '7"': '7" Vinyl',
        '10"': '10" Vinyl',
        '12"': '12" Vinyl',
        'LP': '12" Vinyl'
    },
    "Cassette": "Cassette",
    "CD": "Compact Disc",
    "CDr": {},
    "File": "Digital Media",
    "Flexi-Disc": {},
    "Acetate": {},
    "Lathe Cut": {}
}

DISCOGS_GENRE_MAPPING = {
    "Electronic": "electronic"
}

