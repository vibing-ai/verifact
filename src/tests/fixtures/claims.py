"""Sample claims for testing."""

from src.verifact_agents.claim_detector import Claim

# Political claims
POLITICAL_CLAIMS = [
    Claim(
        text="The United States has the largest military budget in the world.",
        context=0.9,
    ),
    Claim(
        text="The European Union has 27 member states.",
        context=0.8,
    ),
    Claim(
        text="The United Nations was founded in 1945.",
        context=0.85,
    ),
    Claim(
        text="The Paris Climate Agreement was signed in 2016.",
        context=0.75,
    ),
    Claim(
        text="China is the world's largest emitter of carbon dioxide.",
        context=0.8,
    ),
]

# Health claims
HEALTH_CLAIMS = [
    Claim(
        text="Vaccines cause autism.",
        context=0.95,
    ),
    Claim(
        text="Drinking eight glasses of water a day is necessary for good health.",
        context=0.7,
    ),
    Claim(
        text="Regular exercise reduces the risk of heart disease.",
        context=0.85,
    ),
    Claim(
        text="Vitamin C prevents the common cold.",
        context=0.75,
    ),
    Claim(
        text="Eating carrots improves night vision.",
        context=0.65,
    ),
]

# Science claims
SCIENCE_CLAIMS = [
    Claim(
        text="The Earth is flat.",
        context=0.95,
    ),
    Claim(
        text="Humans only use 10% of their brains.",
        context=0.8,
    ),
    Claim(
        text="The Great Wall of China is visible from space with the naked eye.",
        context=0.75,
    ),
    Claim(
        text="Lightning never strikes the same place twice.",
        context=0.7,
    ),
    Claim(
        text="The speed of light is approximately 300,000 kilometers per second.",
        context=0.9,
    ),
]

# Economic claims
ECONOMIC_CLAIMS = [
    Claim(
        text="The United States has the largest economy in the world.",
        context=0.85,
    ),
    Claim(
        text="Bitcoin was the first cryptocurrency.",
        context=0.8,
    ),
    Claim(
        text="The Federal Reserve was established in 1913.",
        context=0.75,
    ),
    Claim(
        text="The Great Depression began with the stock market crash of 1929.",
        context=0.9,
    ),
    Claim(
        text="Amazon is the world's largest online retailer.",
        context=0.8,
    ),
]

# All claims combined
ALL_CLAIMS = POLITICAL_CLAIMS + HEALTH_CLAIMS + SCIENCE_CLAIMS + ECONOMIC_CLAIMS

# Sample claim texts for testing claim detection
SAMPLE_TEXTS = [
    """
    The United States has the largest military budget in the world, spending over $800 billion annually.
    Meanwhile, China is the world's largest emitter of carbon dioxide, producing about 30% of global emissions.
    """,
    
    """
    Many people believe that vaccines cause autism, despite numerous scientific studies disproving this claim.
    It's also commonly stated that humans only use 10% of their brains, which is a widespread misconception.
    """,
    
    """
    The Great Depression began with the stock market crash of 1929, leading to widespread economic hardship.
    During this time, the Federal Reserve, which was established in 1913, failed to prevent the collapse of the banking system.
    """,
    
    """
    The Paris Climate Agreement was signed in 2016 with the goal of limiting global warming.
    The United Nations, founded in 1945 after World War II, has been instrumental in coordinating international climate action.
    """,
]
