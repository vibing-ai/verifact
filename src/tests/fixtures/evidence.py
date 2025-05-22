"""Sample evidence for testing."""

from src.verifact_agents.evidence_hunter import Evidence

# Evidence for political claims
POLITICAL_EVIDENCE = {
    "US military budget": [
        Evidence(
            content="According to the Stockholm International Peace Research Institute (SIPRI), the United States had a military budget of $877 billion in 2022, making it the largest in the world.",
            source="https://www.sipri.org/research/armament-and-disarmament/arms-and-military-expenditure/military-expenditure",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="The U.S. military budget in 2022 was $877 billion, which is more than the next nine countries combined.",
            source="https://www.pgpf.org/chart-archive/0053_defense-comparison",
            relevance=0.9,
            stance="supporting",
        ),
        Evidence(
            content="China had the second-largest military budget at $292 billion in 2022, still significantly less than the United States.",
            source="https://www.sipri.org/sites/default/files/2023-04/2304_fs_milex_2022.pdf",
            relevance=0.8,
            stance="supporting",
        ),
    ],
    "EU member states": [
        Evidence(
            content="The European Union consists of 27 member states: Austria, Belgium, Bulgaria, Croatia, Cyprus, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain and Sweden.",
            source="https://european-union.europa.eu/principles-countries-history/country-profiles_en",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="Following Brexit, which was completed on January 31, 2020, the European Union now has 27 member states.",
            source="https://www.consilium.europa.eu/en/policies/eu-uk-after-referendum/",
            relevance=0.9,
            stance="supporting",
        ),
    ],
    "UN founding": [
        Evidence(
            content="The United Nations officially came into existence on 24 October 1945, when the Charter had been ratified by China, France, the Soviet Union, the United Kingdom, the United States and by a majority of other signatories.",
            source="https://www.un.org/en/about-us/history-of-the-un",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="The United Nations was established after World War II with the aim of preventing future wars, succeeding the ineffective League of Nations.",
            source="https://www.britannica.com/topic/United-Nations",
            relevance=0.85,
            stance="supporting",
        ),
    ],
}

# Evidence for health claims
HEALTH_EVIDENCE = {
    "Vaccines and autism": [
        Evidence(
            content="The scientific consensus is that there is no causal link between vaccines and autism. This has been confirmed by numerous large-scale studies involving millions of children.",
            source="https://www.cdc.gov/vaccinesafety/concerns/autism.html",
            relevance=0.95,
            stance="contradicting",
        ),
        Evidence(
            content="A comprehensive review published in the journal Vaccine in 2014 examined 10 studies involving more than 1.2 million children and found no link between vaccines and autism.",
            source="https://pubmed.ncbi.nlm.nih.gov/24814559/",
            relevance=0.9,
            stance="contradicting",
        ),
        Evidence(
            content="The original 1998 study by Andrew Wakefield that suggested a link between the MMR vaccine and autism was retracted by the journal The Lancet due to serious procedural and ethical flaws.",
            source="https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(10)60175-4/fulltext",
            relevance=0.85,
            stance="contradicting",
        ),
    ],
    "Eight glasses of water": [
        Evidence(
            content="There is no scientific evidence supporting the claim that everyone needs exactly eight glasses of water per day. Water needs vary based on many factors including activity level, climate, and overall health.",
            source="https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/water/art-20044256",
            relevance=0.9,
            stance="contradicting",
        ),
        Evidence(
            content="The Institute of Medicine recommends approximately 3.7 liters (125 ounces) of total water daily for men and 2.7 liters (91 ounces) for women. This includes water from all beverages and foods, not just plain water.",
            source="https://www.nationalacademies.org/news/2004/02/report-sets-dietary-intake-levels-for-water-salt-and-potassium-to-maintain-health-and-reduce-chronic-disease-risk",
            relevance=0.85,
            stance="neutral",
        ),
    ],
}

# Evidence for science claims
SCIENCE_EVIDENCE = {
    "Flat Earth": [
        Evidence(
            content="The Earth is an oblate spheroid, slightly flattened at the poles and bulging at the equator. This has been confirmed by countless observations, measurements, and photographs from space.",
            source="https://www.nasa.gov/image-article/blue-marble-image-earth-from-apollo-17/",
            relevance=0.95,
            stance="contradicting",
        ),
        Evidence(
            content="The ancient Greeks established that the Earth was spherical as early as the 3rd century BCE. Eratosthenes even calculated its circumference with remarkable accuracy using shadows and the angle of the sun.",
            source="https://www.aps.org/publications/apsnews/200606/history.cfm",
            relevance=0.85,
            stance="contradicting",
        ),
        Evidence(
            content="Modern evidence for Earth's spherical shape includes ship disappearance over the horizon, time zone differences, the circular shadow during lunar eclipses, and direct observation from space.",
            source="https://www.scientificamerican.com/article/earth-is-not-flat-heres-how-to-prove-it-to-flat-earthers/",
            relevance=0.9,
            stance="contradicting",
        ),
    ],
    "10% of brain": [
        Evidence(
            content="The myth that humans only use 10% of their brains is not supported by neuroscience. Brain imaging techniques show that all parts of the brain have active functions, even during sleep.",
            source="https://www.scientificamerican.com/article/do-people-only-use-10-percent-of-their-brains/",
            relevance=0.95,
            stance="contradicting",
        ),
        Evidence(
            content="While not all neurons fire simultaneously (which would cause a seizure), brain scans show that most regions of the brain are active during even simple tasks, and virtually all areas are active over the course of a day.",
            source="https://www.bbc.com/future/article/20121112-do-we-only-use-10-of-our-brains",
            relevance=0.9,
            stance="contradicting",
        ),
    ],
}

# Evidence for economic claims
ECONOMIC_EVIDENCE = {
    "US largest economy": [
        Evidence(
            content="As of 2023, the United States has the largest economy in the world with a GDP of approximately $26.95 trillion, followed by China with approximately $17.7 trillion.",
            source="https://www.imf.org/en/Publications/WEO/weo-database/2023/October",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="When measured by purchasing power parity (PPP), China has the largest economy in the world, surpassing the United States in 2017.",
            source="https://www.worldbank.org/en/research/brief/global-economic-prospects",
            relevance=0.9,
            stance="contradicting",
        ),
    ],
    "Bitcoin first cryptocurrency": [
        Evidence(
            content="Bitcoin was created in 2009 by an unknown person or group using the pseudonym Satoshi Nakamoto and was the first decentralized cryptocurrency.",
            source="https://bitcoin.org/bitcoin.pdf",
            relevance=0.95,
            stance="supporting",
        ),
        Evidence(
            content="While Bitcoin was the first successful and widely adopted cryptocurrency, there were earlier attempts at digital currencies such as DigiCash (1989) and B-Money (1998), though they never gained widespread use.",
            source="https://www.investopedia.com/tech/were-there-cryptocurrencies-bitcoin/",
            relevance=0.85,
            stance="neutral",
        ),
    ],
}

# Combined evidence collections
ALL_EVIDENCE = {
    **POLITICAL_EVIDENCE,
    **HEALTH_EVIDENCE,
    **SCIENCE_EVIDENCE,
    **ECONOMIC_EVIDENCE,
}
