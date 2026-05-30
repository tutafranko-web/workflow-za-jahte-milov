"""
Lead source taxonomy: 10 categories x 5 geo tiers.
Used by 03_seed_initial_leads.py AND the daily routine's Faza A.
"""

# Geo tiers
TIERS = {
    1: {
        'label': 'Palma de Mallorca',
        'cities': ['Palma de Mallorca', 'Port Adriano', 'Puerto Portals', 'Andratx', 'Pollensa', 'Alcudia'],
        'country': 'Spain',
        'languages': ['es', 'en'],
    },
    2: {
        'label': 'Balearic + Barcelona',
        'cities': ['Ibiza', 'Mahon', 'Ciutadella', 'Barcelona', 'Sitges', 'Valencia', 'Denia'],
        'country': 'Spain',
        'languages': ['es', 'en'],
    },
    3: {
        'label': 'Italy',
        'cities': ['Naples', 'Sorrento', 'Capri', 'Cagliari', 'Olbia', 'Porto Cervo', 'Palermo', 'Catania', 'Procida'],
        'country': 'Italy',
        'languages': ['it', 'en'],
    },
    4: {
        'label': 'French Riviera',
        'cities': ['Antibes', 'Cannes', 'Nice', 'Saint-Tropez', 'Monaco', 'Toulon', 'La Ciotat'],
        'country': 'France',
        'languages': ['fr', 'en'],
    },
    5: {
        'label': 'Caribbean',
        'cities': ['Tortola', 'St Thomas', 'St Martin', 'Antigua', 'Grenada', 'St Lucia', 'Nassau', 'Road Town'],
        'country': 'Caribbean',
        'languages': ['en'],
    },
}

# 10 lead source categories. Each defines:
#   - label (for template)
#   - search queries (Jinja-style {city} placeholder, list)
#   - template_key (which template to use)
CATEGORIES = {
    'charter': {
        'label': 'charter company',
        'template_key': 'charter',
        'queries': [
            'yacht charter {city}',
            'boat charter {city}',
            'yacht rental {city}',
            'sailing charter {city}',
            'catamaran charter {city}',
        ],
    },
    'crew_agency': {
        'label': 'crew placement agency',
        'template_key': 'crewagency',
        'queries': [
            'yacht crew agency {city}',
            'crew placement {city}',
            'superyacht crew agency {city}',
            # known-name seeds (don't need city)
            '"Bluewater" yacht crew',
            '"YPI Crew" agency',
            '"Camper and Nicholsons" crew',
            '"Dohle Yachts" crew',
            '"Viking Recruitment" yacht',
            '"Wilsonhalligan" crew',
            '"hill robinson" crew',
        ],
    },
    'broker': {
        'label': 'yacht broker',
        'template_key': 'generic',
        'queries': [
            'yacht broker {city}',
            'yacht management company {city}',
            'yacht sales {city}',
        ],
    },
    'daytour': {
        'label': 'day-tour operator',
        'template_key': 'generic',
        'queries': [
            'boat excursion {city}',
            'day trip boat {city}',
            'private boat tour {city}',
            'snorkeling tour boat {city}',
            'sunset cruise {city}',
        ],
    },
    'school': {
        'label': 'sailing school',
        'template_key': 'generic',
        'queries': [
            'sailing school {city}',
            'RYA school {city}',
            'yachtmaster course {city}',
        ],
    },
    'flotilla': {
        'label': 'flotilla operator',
        'template_key': 'charter',
        'queries': [
            'flotilla {city}',
            '"Sunsail" {city}',
            '"The Moorings" {city}',
            '"Dream Yacht Charter" {city}',
            '"Istion Yachting" {city}',
            '"Nautilus Yachting" {city}',
        ],
    },
    'marina': {
        'label': 'marina',
        'template_key': 'generic',
        'queries': [
            'marina {city} contact',
            'port {city} yacht services',
        ],
    },
    'club': {
        'label': 'yacht club',
        'template_key': 'generic',
        'queries': [
            'yacht club {city}',
            'real club nautico {city}',  # Spanish
        ],
    },
    'jobboard_lead': {
        'label': 'yacht crew job board',
        'template_key': 'crewagency',
        'queries': [
            'yacht crew jobs board',
            '"YotSpot" employers',
            '"Crew4Crew" employers',
            '"CrewPass" yacht',
            '"YachtCrewPro" yacht',
            '"Yachting Pages" recruitment',
        ],
    },
    'superyacht': {
        'label': 'superyacht management',
        'template_key': 'generic',
        'queries': [
            'superyacht management {city}',
            'private yacht owner {city}',
            'yacht captain {city} contact',
        ],
    },
}
