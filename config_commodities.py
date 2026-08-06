"""Which input prices move which sectors, and in which direction.

The entity graph already carries ``input_cost`` edges, but they route
*headlines*: a story mentioning copper reaches the sectors exposed to copper.
That measures attention, not cost. A quarter where copper quietly rose 18%
with no headline produces no signal at all, and a week of copper commentary
with a flat price produces a strong one.

This map is the price-based counterpart. Each exposure names the sector, how
much of its cost base the input plausibly represents, and -- the part that
cannot be defaulted -- whether the sector *consumes* the input or *earns*
from it. A weaker rupee is a cost shock for an EMS importer and a tailwind
for an IT exporter, and a map that treated both as "FX exposure" would flag
the wrong half of the watchlist every time the currency moved.

Weights are deliberately coarse. They express "roughly how much of this
sector's margin is at stake", and no band boundary downstream is tight enough
for a second decimal to change the answer. They are not cost-sheet shares and
should not be read as such.
"""

# Yahoo symbols for the front-month contract or spot rate. Kept here rather
# than inline so the fetch layer has no opinion about what it is fetching.
#
# consumer: a price rise raises this sector's costs  -> margin risk
# producer: a price rise raises this sector's realisations -> margin tailwind
COMMODITY_MAP = {
    "copper": {
        "symbol": "HG=F",
        "label": "Copper",
        "unit": "USD/lb",
        "exposure": [
            ("clean_energy", 0.30, "consumer"),
            ("data_center_support", 0.25, "consumer"),
            ("industrial_manufacturing", 0.20, "consumer"),
        ],
    },
    "aluminium": {
        "symbol": "ALI=F",
        "label": "Aluminium",
        "unit": "USD/t",
        "exposure": [
            ("industrial_manufacturing", 0.20, "consumer"),
            ("logistics_heavy_capital", 0.15, "consumer"),
        ],
    },
    "crude": {
        "symbol": "CL=F",
        "label": "Crude oil (WTI)",
        "unit": "USD/bbl",
        "exposure": [
            # Refiners earn on the crack spread, but a crude spike lifts their
            # realisations before it lifts their costs, and the pipeline has
            # no crack-spread series to be more precise with.
            ("big_cap_industries", 0.25, "producer"),
            ("logistics_heavy_capital", 0.25, "consumer"),
            ("fmcg", 0.15, "consumer"),
            ("textiles_apparel", 0.15, "consumer"),
            ("hospitality_travel", 0.20, "consumer"),
        ],
    },
    "steel": {
        "symbol": "HRC=F",
        "label": "Hot-rolled steel",
        "unit": "USD/t",
        "exposure": [
            ("industrial_manufacturing", 0.25, "consumer"),
            ("logistics_heavy_capital", 0.20, "consumer"),
        ],
    },
    "cotton": {
        "symbol": "CT=F",
        "label": "Cotton",
        "unit": "USc/lb",
        "exposure": [("textiles_apparel", 0.35, "consumer")],
    },
    "usdinr": {
        "symbol": "USDINR=X",
        "label": "USD/INR",
        "unit": "INR",
        # The sign convention that makes this map worth having. A rising
        # USDINR is a weaker rupee: imported components cost more, and export
        # billings convert to more rupees.
        "exposure": [
            ("manufacturing_electronics", 0.30, "consumer"),
            ("semiconductors_equipment", 0.30, "consumer"),
            ("midcap_it", 0.30, "producer"),
            ("textiles_apparel", 0.20, "producer"),
            ("cybersecurity", 0.20, "producer"),
        ],
    },
}

# Percentage move over the window at which an input stops being noise. Below
# this the series is reported but no sector shock is raised -- commodity
# futures move a percent or two on nothing in particular, and a briefing that
# flagged every wiggle would train the reader to ignore the section.
MATERIAL_MOVE_PCT = 5.0

# Move at which the shock is called severe rather than notable.
SEVERE_MOVE_PCT = 12.0

# Trading days compared. A month is long enough that a single volatile
# session cannot define the trend, short enough to still be news.
WINDOW_DAYS = 30
