"""Memory-seeded candidates, deliberately NOT live-verified."""

import json
import re
from pathlib import Path

GROUPS = {
    "software": """Stripe|Figma|Notion|Airtable|Asana|Linear|Vercel|Netlify|Supabase|PlanetScale|Neon|Render|Railway|Fly.io|Replit|GitLab|GitHub|Docker|HashiCorp|Pulumi|Snyk|Sonar|Sourcegraph|Postman|Insomnia|Kong|Temporal|Confluent|Databricks|Snowflake|MongoDB|Elastic|Redis|Cockroach Labs|ClickHouse|SingleStore|Starburst|dbt Labs|Fivetran|Airbyte|Dagster|Prefect|Astronomer|MotherDuck|Rill Data|Hex|Mode|Sigma Computing|ThoughtSpot|Looker|Amplitude|Mixpanel|Heap|Pendo|FullStory|LaunchDarkly|Split|Statsig|Optimizely|Eppo|GrowthBook|Segment|RudderStack|Hightouch|Census|Customer.io|Braze|Iterable|Klaviyo|Attentive|Twilio|SendGrid|MessageBird|Telnyx|Plivo|Vonage|Daily|LiveKit|Agora|Mux|Cloudflare|Fastly|Akamai|Tailscale|Twingate|Teleport|Okta|Auth0|Clerk|WorkOS|Stytch|Descope|FusionAuth|OneLogin|Duo Security|1Password|Bitwarden|Dashlane|Keeper Security|BeyondTrust|CyberArk|Palo Alto Networks|CrowdStrike|SentinelOne|Wiz|Orca Security|Lacework|Aqua Security|Sysdig|Chainguard|Socket|Semgrep|Veracode|Checkmarx|GitGuardian|Truffle Security|Doppler|Infisical|Vanta|Drata|Secureframe|Sprinto|Thoropass|AuditBoard|OneTrust|BigID|Securiti|Immuta|Privacera|Collibra|Alation|Atlan|Monte Carlo|Bigeye|Soda|Anomalo|Metaplane|Datadog|New Relic|Grafana Labs|Honeycomb|Lightstep|Chronosphere|Cribl|Coralogix|Logz.io|Sentry|Bugsnag|Rollbar|Raygun|Airbrake|Better Stack|Axiom|Highlight|OpenReplay|PostHog|June|Plausible|Fathom Analytics|Cal.com|Calendly|SavvyCal|Reclaim|Clockwise|Motion|Superhuman|Front|Missive|Shortwave|Spark|Grammarly|DeepL|Lokalise|Phrase|Smartling|Transifex|Crowdin|Webflow|Framer|Squarespace|Wix|Duda|Contentful|Sanity|Strapi|Storyblok|Prismic|Builder.io|Hygraph|DatoCMS|Ghost|WordPress|Automattic|Shopify|BigCommerce|Commerce Layer|Medusa|Saleor|Vendure|commercetools|Fabric|Bolt|FastSpring|Paddle|Lemon Squeezy|Chargebee|Recurly|Zuora|Maxio|Orb|Metronome|Lago|Moesif|Togai|Finix|Adyen|Checkout.com|Plaid|Modern Treasury|Unit|Treasury Prime|Synctera|Increase|Column|Lithic|Marqeta|Highnote|Ramp|Brex|Mercury|Rho|Novo|Bluevine|Relay|Airwallex|Wise|Revolut|Monzo|N26|Chime|Current|Varo|Dave|SoFi|Affirm|Klarna|Afterpay|Sezzle|Zip|Robinhood|Coinbase|Kraken|Gemini|BitGo|Fireblocks|Anchorage Digital|Chainalysis|TRM Labs|Elliptic|Circle|Paxos|Ripple|Stellar Development Foundation|OpenSea|Alchemy|QuickNode|Infura|Consensys|Tenderly|Blockdaemon|Figment""",
    "ai": """OpenAI|Anthropic|Cohere|Mistral AI|AI21 Labs|Hugging Face|Together AI|Fireworks AI|Groq|Cerebras|SambaNova|RunPod|Lambda|CoreWeave|Modal|Baseten|Replicate|Anyscale|Scale AI|Labelbox|Snorkel AI|Weights & Biases|Comet|Neptune AI|Arize AI|Fiddler AI|WhyLabs|Arthur AI|Galileo|Braintrust|LangChain|LlamaIndex|Pinecone|Weaviate|Qdrant|Milvus|Zilliz|Chroma|LanceDB|Unstructured|Lexion|Harvey|Hebbia|Glean|Sierra|Decagon|Ada|Intercom|Forethought|Moveworks|Aisera|Observe.AI|Cresta|Gong|Clari|Avoma|Otter.ai|Fireflies.ai|Fathom|Granola|Mem|Rewind|Limitless|Perplexity|You.com|Phind|Cursor|Codeium|Tabnine|Augment Code|Poolside|Magic|Cognition|Factory|Devin AI|Reka AI|Character.AI|ElevenLabs|PlayHT|Cartesia|Hume AI|AssemblyAI|Deepgram|Speechmatics|Rev|Descript|Runway|Pika|Luma AI|Stability AI|Midjourney|Ideogram|Black Forest Labs|Krea|Synthesia|HeyGen|D-ID|Tavus""",
    "aviation,defence": """SpaceX|Blue Origin|Rocket Lab|Relativity Space|Stoke Space|Firefly Aerospace|Astra|ABL Space Systems|Ursa Major|Impulse Space|Varda Space Industries|Astranis|Apex Space|True Anomaly|Anduril|Shield AI|Skydio|Saronic|Saildrone|Epirus|Helsing|Palantir|Rebellion Defense|Second Front Systems|Vannevar Labs|Primer|Hadrian|Machina Labs|Divergent|Joby Aviation|Archer Aviation|Wisk Aero|Beta Technologies|Eve Air Mobility|Boom Supersonic|Hermeus|Venus Aerospace|Reliable Robotics|Xwing|Merlin Labs|Zipline|Wing|Matternet|Elroy Air|Natilus|REGENT|Electra|ZeroAvia|Universal Hydrogen|Heart Aerospace""",
    "health tech": """Tempus|Flatiron Health|Benchling|Recursion|Insitro|Generate Biomedicines|EvolutionaryScale|Cradle|AbCellera|Absci|Owkin|PathAI|Paige|Proscia|Viz.ai|Aidoc|Qure.ai|Butterfly Network|HeartFlow|Cleerly|Eko Health|AliveCor|iRhythm|Dexcom|Insulet|Tandem Diabetes Care|Omada Health|Virta Health|Hinge Health|Sword Health|Spring Health|Modern Health|Lyra Health|Headspace|Calm|Talkspace|Grow Therapy|Alma|Headway|Rula|Charlie Health|Equip|Maven Clinic|Carrot Fertility|Progyny|Kindbody|Tia|One Medical|Forward|Carbon Health|Cityblock Health|Devoted Health|Oscar Health|Clover Health|Cedar|Turquoise Health|Nuna|Komodo Health|Truveta|HealthVerity|Abridge|Ambience Healthcare|Suki|Nabla|Augmedix""",
    "quantitative finance": """Jane Street|Hudson River Trading|Citadel|Citadel Securities|Two Sigma|D. E. Shaw|Jump Trading|Optiver|IMC Trading|DRW|Akuna Capital|Flow Traders|Virtu Financial|Tower Research|XTX Markets|G-Research|Man AHL|Winton|WorldQuant|Millennium|Point72|Balyasny|Schonfeld|Cubist|Squarepoint|Qube Research|Five Rings|Old Mission|Belvedere Trading|Wolverine Trading|SIG|Maven Securities|Da Vinci|VivCourt|Tibra|TransMarket Group|Quantlab|Headlands Technologies|Radix Trading|Ansatz Capital""",
}
rows = []
for category, names in GROUPS.items():
    for name in names.split("|"):
        token = re.sub(r"[^a-z0-9]", "", name.lower())
        rows.append(
            dict(
                id=token,
                name=name,
                domain=token + ".com",
                platform="greenhouse",
                token=token,
                tags=category.split(","),
                size="unknown",
                verified=False,
                notes="Memory-seeded candidate. Platform, token, domain and category require verification.",
            )
        )
# Best-known platform guesses; all remain unverified.
for row in rows:
    if row["name"] in [
        "OpenAI",
        "Notion",
        "Linear",
        "Ramp",
        "Cursor",
        "Cohere",
        "ElevenLabs",
        "Vercel",
        "Modal",
        "Anthropic",
    ]:
        row["platform"] = "ashby"
    if row["name"] in ["Netflix", "Plaid", "Palantir", "Lever", "Wealthfront"]:
        row["platform"] = "lever"
Path("data/registry.seed.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
Path("REVIEW_REGISTRY.md").write_text(
    "# Unverified company candidates\n\nAll domains, platforms and tokens are guesses from memory, not live-verified. Check with `firstlook registry verify --all`; correct failed guesses with discovery or Registry editing.\n\n| Company | Domain | Platform | Token | Verified |\n|---|---|---|---|---|\n"
    + "".join(f"| {r['name']} | {r['domain']} | {r['platform']} | {r['token']} | |\n" for r in rows)
)
print(f"{len(rows)} unverified companies")
