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
    extraartists:  list[DiscogsReleaseExtraArtist]
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


