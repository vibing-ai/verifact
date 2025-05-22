"""Sample verdicts for testing."""

from src.verifact_agents.verdict_writer import Verdict

# Verdicts for political claims
POLITICAL_VERDICTS = [
    Verdict(
        claim="The United States has the largest military budget in the world.",
        verdict="true",
        confidence=0.95,
        explanation="Multiple reliable sources confirm that the United States has the largest military budget in the world. According to the Stockholm International Peace Research Institute (SIPRI), the US military budget was $877 billion in 2022, which is more than the next nine countries combined. China had the second-largest budget at $292 billion, significantly less than the US.",
        sources=[
            "https://www.sipri.org/research/armament-and-disarmament/arms-and-military-expenditure/military-expenditure",
            "https://www.pgpf.org/chart-archive/0053_defense-comparison",
            "https://www.sipri.org/sites/default/files/2023-04/2304_fs_milex_2022.pdf",
        ],
    ),
    Verdict(
        claim="The European Union has 27 member states.",
        verdict="true",
        confidence=0.98,
        explanation="The European Union currently consists of 27 member states. Following the United Kingdom's departure (Brexit) which was completed on January 31, 2020, the EU membership decreased from 28 to 27 countries. The current member states are: Austria, Belgium, Bulgaria, Croatia, Cyprus, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain and Sweden.",
        sources=[
            "https://european-union.europa.eu/principles-countries-history/country-profiles_en",
            "https://www.consilium.europa.eu/en/policies/eu-uk-after-referendum/",
        ],
    ),
    Verdict(
        claim="The United Nations was founded in 1945.",
        verdict="true",
        confidence=0.99,
        explanation="The United Nations was indeed founded in 1945. The UN officially came into existence on October 24, 1945, when its Charter was ratified by China, France, the Soviet Union, the United Kingdom, the United States, and a majority of other signatories. The organization was established after World War II with the aim of preventing future wars, succeeding the ineffective League of Nations.",
        sources=[
            "https://www.un.org/en/about-us/history-of-the-un",
            "https://www.britannica.com/topic/United-Nations",
        ],
    ),
]

# Verdicts for health claims
HEALTH_VERDICTS = [
    Verdict(
        claim="Vaccines cause autism.",
        verdict="false",
        confidence=0.98,
        explanation="The claim that vaccines cause autism is false. The scientific consensus, based on numerous large-scale studies involving millions of children, is that there is no causal link between vaccines and autism. A comprehensive review published in the journal Vaccine in 2014 examined 10 studies involving more than 1.2 million children and found no link. The original 1998 study by Andrew Wakefield that suggested a link between the MMR vaccine and autism was retracted by the journal The Lancet due to serious procedural and ethical flaws.",
        sources=[
            "https://www.cdc.gov/vaccinesafety/concerns/autism.html",
            "https://pubmed.ncbi.nlm.nih.gov/24814559/",
            "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(10)60175-4/fulltext",
        ],
    ),
    Verdict(
        claim="Drinking eight glasses of water a day is necessary for good health.",
        verdict="partially true",
        confidence=0.75,
        explanation="The claim that drinking exactly eight glasses of water per day is necessary for good health is partially true. While adequate hydration is essential for health, there is no scientific evidence supporting the specific recommendation of eight glasses. Water needs vary based on many factors including activity level, climate, and overall health. The Institute of Medicine recommends approximately 3.7 liters (125 ounces) of total water daily for men and 2.7 liters (91 ounces) for women, but this includes water from all beverages and foods, not just plain water. The '8x8' rule (eight 8-ounce glasses) may be a useful general guideline for some people, but it's not a scientific requirement for everyone.",
        sources=[
            "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/water/art-20044256",
            "https://www.nationalacademies.org/news/2004/02/report-sets-dietary-intake-levels-for-water-salt-and-potassium-to-maintain-health-and-reduce-chronic-disease-risk",
        ],
    ),
]

# Verdicts for science claims
SCIENCE_VERDICTS = [
    Verdict(
        claim="The Earth is flat.",
        verdict="false",
        confidence=0.99,
        explanation="The claim that the Earth is flat is false. The Earth is an oblate spheroid, slightly flattened at the poles and bulging at the equator. This has been confirmed by countless observations, measurements, and photographs from space. The ancient Greeks established that the Earth was spherical as early as the 3rd century BCE, with Eratosthenes even calculating its circumference with remarkable accuracy. Modern evidence for Earth's spherical shape includes ship disappearance over the horizon, time zone differences, the circular shadow during lunar eclipses, and direct observation from space.",
        sources=[
            "https://www.nasa.gov/image-article/blue-marble-image-earth-from-apollo-17/",
            "https://www.aps.org/publications/apsnews/200606/history.cfm",
            "https://www.scientificamerican.com/article/earth-is-not-flat-heres-how-to-prove-it-to-flat-earthers/",
        ],
    ),
    Verdict(
        claim="Humans only use 10% of their brains.",
        verdict="false",
        confidence=0.95,
        explanation="The claim that humans only use 10% of their brains is false. This popular myth is not supported by neuroscience. Brain imaging techniques show that all parts of the brain have active functions, even during sleep. While not all neurons fire simultaneously (which would cause a seizure), brain scans show that most regions of the brain are active during even simple tasks, and virtually all areas are active over the course of a day. The brain is an energy-intensive organ, consuming about 20% of the body's energy despite being only 2% of its weight, which would be evolutionarily inefficient if 90% were unused.",
        sources=[
            "https://www.scientificamerican.com/article/do-people-only-use-10-percent-of-their-brains/",
            "https://www.bbc.com/future/article/20121112-do-we-only-use-10-of-our-brains",
        ],
    ),
    Verdict(
        claim="There is intelligent alien life in our galaxy.",
        verdict="unverifiable",
        confidence=0.6,
        explanation="The claim that there is intelligent alien life in our galaxy is currently unverifiable. While scientific consensus suggests that the mathematical probability of extraterrestrial life existing somewhere in our vast galaxy is high given the billions of stars and planets, we currently have no direct evidence of intelligent alien civilizations. The search for extraterrestrial intelligence (SETI) has been ongoing for decades without confirmed contact. The Fermi Paradox highlights this contradiction: despite high probability estimates, we have yet to detect any signs of alien intelligence. Until we have concrete evidence one way or the other, this claim remains unverifiable with current scientific capabilities.",
        sources=[
            "https://www.seti.org/search-extraterrestrial-life",
            "https://www.nasa.gov/feature/goddard/2020/are-we-alone-in-the-universe-nasa-s-search-for-life",
            "https://www.scientificamerican.com/article/the-search-for-extraterrestrial-intelligence/",
        ],
    ),
]

# Verdicts for economic claims
ECONOMIC_VERDICTS = [
    Verdict(
        claim="The United States has the largest economy in the world.",
        verdict="partially true",
        confidence=0.85,
        explanation="The claim that the United States has the largest economy in the world is partially true, depending on how economic size is measured. When measured by nominal GDP, the United States does have the largest economy with approximately $26.95 trillion as of 2023, followed by China with approximately $17.7 trillion. However, when measured by purchasing power parity (PPP), which adjusts for price differences between countries, China has the largest economy in the world, having surpassed the United States in 2017. Both metrics are valid ways to measure economic size, but they answer different questions: nominal GDP is better for international comparisons involving trade and financial flows, while PPP is better for comparing living standards.",
        sources=[
            "https://www.imf.org/en/Publications/WEO/weo-database/2023/October",
            "https://www.worldbank.org/en/research/brief/global-economic-prospects",
        ],
    ),
    Verdict(
        claim="Bitcoin was the first cryptocurrency.",
        verdict="true",
        confidence=0.9,
        explanation="The claim that Bitcoin was the first cryptocurrency is true, with some nuance. Bitcoin was created in 2009 by an unknown person or group using the pseudonym Satoshi Nakamoto and was the first decentralized cryptocurrency to gain widespread adoption and use. While there were earlier attempts at digital currencies such as DigiCash (1989) and B-Money (1998), these systems either were centralized or remained theoretical and never gained widespread use. Bitcoin was revolutionary because it solved the 'double-spending problem' without requiring a trusted third party, through its blockchain technology and proof-of-work consensus mechanism.",
        sources=[
            "https://bitcoin.org/bitcoin.pdf",
            "https://www.investopedia.com/tech/were-there-cryptocurrencies-bitcoin/",
        ],
    ),
]

# Combined verdicts
ALL_VERDICTS = POLITICAL_VERDICTS + HEALTH_VERDICTS + SCIENCE_VERDICTS + ECONOMIC_VERDICTS
