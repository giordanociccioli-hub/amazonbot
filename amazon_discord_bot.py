"""
╔══════════════════════════════════════════════════════════════╗
║       🤖  AMAZON RESELLING BOT — Discord Slash Commands      ║
║  Comandi: /avvia /ferma /stato /controlla /prodotti          ║
╚══════════════════════════════════════════════════════════════╝

INSTALLAZIONE:
    pip install discord.py requests beautifulsoup4

AVVIO:
    python amazon_discord_bot.py
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import json, os, re, logging, asyncio
from datetime import datetime
from statistics import median

# ══════════════════════════════════════════════════════════════
#  📝  LOGGING
# ══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("AmazonBot")

# ══════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURAZIONE
# ══════════════════════════════════════════════════════════════
CONFIG = {
    "DISCORD_BOT_TOKEN":      "MTQ5NjQ4Mjg4OTg1MDY4MzUxMw.G0yt1b.-RPCZUTh1N2A3oOAErXrWngdYD-kJ7d0byYpIc",
    "DISCORD_WEBHOOK_URL":    "https://discord.com/api/webhooks/1496469735846445106/3Hq4C4A0n-0NaW33wC-93o6eDCqr2PoDKvo1vvb4iEAMo1duX0mMuRFnwMA311LnR2-v",
    "CHECK_INTERVAL_MINUTES": 60,
    "MIN_RESELL_PROFIT":      20.0,
    "MAX_EBAY_RESULTS":       12,
    "MAX_SUBITO_RESULTS":     12,
    "REQUEST_DELAY":          2.5,
    "MAX_RETRIES":            2,
}

# ── Stato globale del bot ────────────────────────────────────
STATO = {
    "attivo":           False,
    "ultimo_controllo": None,
    "opportunita_trovate": 0,
    "cicli_completati": 0,
    "canale_notifiche": None,   # ID canale dove mandare i report
}

PREZZI_FILE  = "prezzi_salvati.json"
STORICO_FILE = "storico_opportunita.json"

# ══════════════════════════════════════════════════════════════
#  📦  ARTICOLI
# ══════════════════════════════════════════════════════════════
ARTICOLI = [
    # ─── 🍎 APPLE
    {"nome": "Apple AirPods Pro 2 (USB-C)",      "url": "https://www.amazon.it/dp/B0BDHWDR12", "query_rivendita": "AirPods Pro 2 USB-C",            "brand": "Apple",       "categoria": "Audio"},
    {"nome": "Apple Watch Series 10 GPS 42mm",   "url": "https://www.amazon.it/dp/B0DGHQL22R", "query_rivendita": "Apple Watch Series 10 42mm",    "brand": "Apple",       "categoria": "Wearable"},
    {"nome": "Apple iPad 10ª gen 64GB",          "url": "https://www.amazon.it/dp/B0BJLXMVMV", "query_rivendita": "iPad 10 generazione 64GB",      "brand": "Apple",       "categoria": "Tablet"},
    {"nome": "Apple AirTag x4",                  "url": "https://www.amazon.it/dp/B0932QJ2JZ", "query_rivendita": "Apple AirTag 4 pezzi",          "brand": "Apple",       "categoria": "Accessori"},
    {"nome": "Apple MacBook Air M2 13\"",        "url": "https://www.amazon.it/dp/B0B3BVWJ6X", "query_rivendita": "MacBook Air M2 13 pollici",     "brand": "Apple",       "categoria": "Laptop"},
    # ─── 📱 SAMSUNG
    {"nome": "Samsung Galaxy Buds3 Pro",         "url": "https://www.amazon.it/dp/B0D5C13JL9", "query_rivendita": "Samsung Galaxy Buds3 Pro",      "brand": "Samsung",     "categoria": "Audio"},
    {"nome": "Samsung Galaxy Watch7 44mm",       "url": "https://www.amazon.it/dp/B0D4C9Q4PN", "query_rivendita": "Samsung Galaxy Watch 7 44mm",   "brand": "Samsung",     "categoria": "Wearable"},
    {"nome": "Samsung T7 SSD 1TB",               "url": "https://www.amazon.it/dp/B08GTYFC37", "query_rivendita": "Samsung T7 SSD 1TB",            "brand": "Samsung",     "categoria": "Storage"},
    # ─── 🎧 SONY
    {"nome": "Sony WH-1000XM5 Cuffie ANC",       "url": "https://www.amazon.it/dp/B09XS7JWHH", "query_rivendita": "Sony WH-1000XM5",               "brand": "Sony",        "categoria": "Audio"},
    {"nome": "Sony WF-1000XM5 Auricolari",       "url": "https://www.amazon.it/dp/B0C33XXS56", "query_rivendita": "Sony WF-1000XM5",               "brand": "Sony",        "categoria": "Audio"},
    # ─── 🖱️ LOGITECH
    {"nome": "Logitech MX Master 3S",            "url": "https://www.amazon.it/dp/B09HM94VDS", "query_rivendita": "Logitech MX Master 3S",         "brand": "Logitech",    "categoria": "Periferiche"},
    {"nome": "Logitech MX Keys S",               "url": "https://www.amazon.it/dp/B09DTQCXZD", "query_rivendita": "Logitech MX Keys S",            "brand": "Logitech",    "categoria": "Periferiche"},
    {"nome": "Logitech G502 X Gaming",           "url": "https://www.amazon.it/dp/B09NCRRYVH", "query_rivendita": "Logitech G502 X",               "brand": "Logitech",    "categoria": "Gaming"},
    {"nome": "Logitech G Pro X Superlight 2",    "url": "https://www.amazon.it/dp/B09NGRQ256", "query_rivendita": "Logitech G Pro X Superlight 2", "brand": "Logitech",    "categoria": "Gaming"},
    # ─── 🔊 BOSE
    {"nome": "Bose QuietComfort 45",             "url": "https://www.amazon.it/dp/B098FKXT8L", "query_rivendita": "Bose QuietComfort 45",          "brand": "Bose",        "categoria": "Audio"},
    {"nome": "Bose SoundLink Flex",              "url": "https://www.amazon.it/dp/B099TJGJ91", "query_rivendita": "Bose SoundLink Flex",           "brand": "Bose",        "categoria": "Audio"},
    # ─── 🎮 PLAYSTATION
    {"nome": "PlayStation 5 Slim (disc)",        "url": "https://www.amazon.it/dp/B0CL5KNB9M", "query_rivendita": "PlayStation 5 Slim disc",       "brand": "PlayStation", "categoria": "Console"},
    {"nome": "DualSense Controller Bianco",      "url": "https://www.amazon.it/dp/B08H99BPJN", "query_rivendita": "DualSense PS5 bianco",          "brand": "PlayStation", "categoria": "Gaming"},
    {"nome": "DualSense Edge Controller",        "url": "https://www.amazon.it/dp/B0BCTXPQK7", "query_rivendita": "DualSense Edge PS5",            "brand": "PlayStation", "categoria": "Gaming"},
    {"nome": "PlayStation VR2",                  "url": "https://www.amazon.it/dp/B0BCT9KN4W", "query_rivendita": "PlayStation VR2 PSVR2",         "brand": "PlayStation", "categoria": "Gaming"},
    {"nome": "Sony Pulse 3D Cuffie PS5",         "url": "https://www.amazon.it/dp/B08FC5L3RG", "query_rivendita": "Sony Pulse 3D PS5",             "brand": "PlayStation", "categoria": "Gaming"},
    # ─── 🟥 XBOX
    {"nome": "Xbox Series X 1TB",                "url": "https://www.amazon.it/dp/B08H75RTZ8", "query_rivendita": "Xbox Series X 1TB",             "brand": "Xbox",        "categoria": "Console"},
    {"nome": "Xbox Series S 512GB",              "url": "https://www.amazon.it/dp/B08H93ZRK9", "query_rivendita": "Xbox Series S 512GB",           "brand": "Xbox",        "categoria": "Console"},
    {"nome": "Controller Xbox Wireless Nero",    "url": "https://www.amazon.it/dp/B08DF26MLL", "query_rivendita": "controller Xbox wireless nero",  "brand": "Xbox",        "categoria": "Gaming"},
    {"nome": "Xbox Elite Controller Series 2",   "url": "https://www.amazon.it/dp/B07SFKTLZM", "query_rivendita": "Xbox Elite Controller Series 2", "brand": "Xbox",       "categoria": "Gaming"},
    # ─── 🕹️ NINTENDO
    {"nome": "Nintendo Switch 2",                "url": "https://www.amazon.it/dp/B0DJG3CQLN", "query_rivendita": "Nintendo Switch 2 console",     "brand": "Nintendo",    "categoria": "Console"},
    {"nome": "Nintendo Switch OLED",             "url": "https://www.amazon.it/dp/B098RL6SBK", "query_rivendita": "Nintendo Switch OLED",          "brand": "Nintendo",    "categoria": "Console"},
    {"nome": "Nintendo Switch Pro Controller",   "url": "https://www.amazon.it/dp/B01NAWKZVS", "query_rivendita": "Nintendo Switch Pro Controller", "brand": "Nintendo",   "categoria": "Gaming"},
    {"nome": "Nintendo Joy-Con Coppia Neon",     "url": "https://www.amazon.it/dp/B01N6QKT7H", "query_rivendita": "Nintendo Joy-Con coppia neon",  "brand": "Nintendo",    "categoria": "Gaming"},
    {"nome": "Nintendo Switch 2 Pro Controller", "url": "https://www.amazon.it/dp/B0DJG5M4JC", "query_rivendita": "Nintendo Switch 2 Pro Controller","brand": "Nintendo", "categoria": "Gaming"},
    # ─── 🥽 META
    {"nome": "Meta Quest 3 128GB",               "url": "https://www.amazon.it/dp/B0CCT2NB11", "query_rivendita": "Meta Quest 3 128GB VR",         "brand": "Meta",        "categoria": "VR/Gaming"},
    {"nome": "Meta Quest 3S 128GB",              "url": "https://www.amazon.it/dp/B0D37JB25J", "query_rivendita": "Meta Quest 3S 128GB VR",        "brand": "Meta",        "categoria": "VR/Gaming"},
    # ─── ⚡ ANKER
    {"nome": "Anker GaN 65W Caricatore",         "url": "https://www.amazon.it/dp/B09316GXSC", "query_rivendita": "Anker caricatore GaN 65W",      "brand": "Anker",       "categoria": "Accessori"},
    {"nome": "Anker PowerCore 26800mAh",         "url": "https://www.amazon.it/dp/B01JIWQOS6", "query_rivendita": "Anker PowerCore 26800",         "brand": "Anker",       "categoria": "Accessori"},
]

BRAND_EMOJI = {
    "Apple": "🍎", "Samsung": "📱", "Logitech": "🖱️", "Sony": "🎧",
    "Bose": "🔊", "PlayStation": "🎮", "Xbox": "🟥", "Nintendo": "🕹️",
    "Meta": "🥽", "Anker": "⚡",
}
CAT_EMOJI = {
    "Console": "🕹️", "Gaming": "🎮", "VR/Gaming": "🥽", "Audio": "🎧",
    "Wearable": "⌚", "Laptop": "💻", "Tablet": "📱", "Periferiche": "🖱️",
    "Accessori": "⚡", "Storage": "💾",
}
CAT_COLORI = {
    "Console": 0xFF2D2D, "Gaming": 0xE60012, "VR/Gaming": 0x0064E0,
    "Audio": 0x1DB954, "Wearable": 0x007AFF, "Laptop": 0xA2AAAD,
    "Tablet": 0x6C8EBF, "Periferiche": 0x00B4D8, "Accessori": 0xFF9900,
    "Storage": 0xFFCC00,
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS_AMAZON  = {"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9",
                   "Accept-Encoding": "gzip, deflate, br", "DNT": "1",
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
HEADERS_GENERIC = {"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9",
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

# ══════════════════════════════════════════════════════════════
#  🛠️  UTILITÀ
# ══════════════════════════════════════════════════════════════
def safe_get(url, headers, label=""):
    for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt < CONFIG["MAX_RETRIES"]:
                time_mod.sleep(3)
            else:
                log.error(f"[{label}] Tutti i tentativi falliti: {e}")
    return None

import time as time_mod

def pulisci_prezzo(testo):
    try:
        t = re.sub(r"[^\d,\.]", "", testo.replace("EUR","").replace("€","").strip())
        t = t.replace(".","").replace(",",".")
        val = float(t)
        return val if val > 0.5 else None
    except Exception:
        return None

def margine_stelle(margine):
    n = min(5, max(1, int(margine // 20)))
    return "⭐" * n + "☆" * (5 - n)

def carica_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salva_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════════════
#  🔍  SCRAPING
# ══════════════════════════════════════════════════════════════
def ottieni_prezzo_amazon(url):
    resp = safe_get(url, HEADERS_AMAZON, "Amazon")
    if not resp:
        return None, None
    soup = BeautifulSoup(resp.content, "html.parser")
    for sel in [
        ".priceToPay .a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice",
        ".a-price .a-offscreen", "#price_inside_buybox",
        "#apex_offerDisplay_desktop .a-price .a-offscreen",
        "#corePrice_feature_div .a-price .a-offscreen", ".apexPriceToPay .a-offscreen",
    ]:
        el = soup.select_one(sel)
        if el:
            testo = el.get_text().strip()
            val   = pulisci_prezzo(testo)
            if val:
                return val, testo
    return None, None

def ottieni_prezzi_ebay(query):
    q    = requests.utils.quote(query)
    url  = f"https://www.ebay.it/sch/i.html?_nkw={q}&LH_BIN=1&LH_ItemCondition=1000&_sop=15&_ipg=25"
    resp = safe_get(url, HEADERS_GENERIC, "eBay")
    if not resp:
        return []
    soup   = BeautifulSoup(resp.content, "html.parser")
    prezzi = []
    for el in soup.select(".s-item__price")[:CONFIG["MAX_EBAY_RESULTS"] * 2]:
        val = pulisci_prezzo(el.get_text().strip().split(" a ")[0])
        if val and val > 1:
            prezzi.append(val)
            if len(prezzi) >= CONFIG["MAX_EBAY_RESULTS"]:
                break
    return prezzi

def ottieni_prezzi_subito(query):
    q    = requests.utils.quote(query)
    url  = f"https://www.subito.it/annunci-italia/vendita/usato/?q={q}&shp=y"
    resp = safe_get(url, HEADERS_GENERIC, "Subito")
    if not resp:
        return []
    soup   = BeautifulSoup(resp.content, "html.parser")
    items  = soup.select("p[class*='price']") or soup.find_all(string=re.compile(r"€\s*\d"))
    prezzi = []
    for el in items:
        testo = el.get_text() if hasattr(el, "get_text") else str(el)
        val   = pulisci_prezzo(testo)
        if val and val > 1:
            prezzi.append(val)
            if len(prezzi) >= CONFIG["MAX_SUBITO_RESULTS"]:
                break
    return prezzi

def calcola_prezzo_rivendita(query):
    pe = ottieni_prezzi_ebay(query)
    time_mod.sleep(1)
    ps = ottieni_prezzi_subito(query)
    tutti = pe + ps
    if not tutti:
        return None, "nessun dato"
    med      = median(tutti)
    filtrati = [p for p in tutti if med * 0.50 <= p <= med * 1.50] or tutti
    return round(median(filtrati), 2), f"eBay({len(pe)}) + Subito({len(ps)})"

# ══════════════════════════════════════════════════════════════
#  📨  INVIO NOTIFICHE DISCORD (webhook)
# ══════════════════════════════════════════════════════════════
def invia_discord_opportunita(art, p_amazon, p_riv, margine, pct, fonte):
    b_ico  = BRAND_EMOJI.get(art["brand"], "🛒")
    cat    = art.get("categoria", "")
    colore = CAT_COLORI.get(cat, 0xFF9900)
    fields = [
        {"name": "🛒 Acquisto Amazon",    "value": f"```fix\n€{p_amazon:.2f}\n```",              "inline": True},
        {"name": "💵 Rivendita stimata",  "value": f"```fix\n€{p_riv:.2f}\n```",                 "inline": True},
        {"name": "💰 Margine netto",      "value": f"```diff\n+€{margine:.2f} (+{pct:.1f}%)\n```","inline": True},
        {"name": "📈 Attrattività",       "value": margine_stelle(margine),                       "inline": True},
        {"name": f"{CAT_EMOJI.get(cat,'📦')} Categoria", "value": cat,                           "inline": True},
        {"name": "📊 Fonte dati",         "value": fonte,                                         "inline": True},
        {"name": "🔗 Link diretto",       "value": art["url"],                                    "inline": False},
    ]
    embed = {
        "title":       f"{b_ico}  {art['nome']}",
        "url":         art["url"],
        "description": f"✅  **Opportunità di rivendita rilevata!**\nMargine potenziale: **+€{margine:.2f}** ({pct:.1f}%)",
        "color":       colore,
        "fields":      fields,
        "footer":      {"text": f"🤖 Amazon Price Bot  •  {datetime.now().strftime('%d/%m/%Y  %H:%M')}"},
    }
    try:
        requests.post(CONFIG["DISCORD_WEBHOOK_URL"], json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        log.error(f"Discord webhook errore: {e}")

def invia_report_webhook(risultati, ora, totale):
    if not risultati:
        embed = {
            "title":       "📊  Report — Nessuna opportunità",
            "description": (f"😴  Nessun articolo supera il margine minimo di **€{CONFIG['MIN_RESELL_PROFIT']:.0f}**.\n"
                            f"⏱️  Prossimo controllo tra **{CONFIG['CHECK_INTERVAL_MINUTES']} min**."),
            "color":  0x555555,
            "footer": {"text": f"🤖 Amazon Price Bot  •  {ora}"},
        }
        try:
            requests.post(CONFIG["DISCORD_WEBHOOK_URL"], json={"embeds": [embed]}, timeout=10)
        except Exception:
            pass
        return

    per_cat = {}
    for r in risultati:
        per_cat.setdefault(r["categoria"], []).append(r)

    fields = []
    for cat, items in sorted(per_cat.items()):
        c_ico = CAT_EMOJI.get(cat, "📦")
        righe = ""
        for item in sorted(items, key=lambda x: x["margine"], reverse=True):
            b_ico = BRAND_EMOJI.get(item["brand"], "🛒")
            righe += (
                f"{b_ico} **{item['nome']}**  {margine_stelle(item['margine'])}\n"
                f"> 🛒 €{item['prezzo_amazon']:.2f}  →  💵 €{item['prezzo_rivendita']:.2f}  →  💰 **+€{item['margine']:.2f}**\n"
                f"> 🔗 [Acquista su Amazon]({item['url']})\n\n"
            )
        fields.append({"name": f"{c_ico}  {cat}  —  {len(items)} articolo/i", "value": righe.strip(), "inline": False})

    best   = max(risultati, key=lambda x: x["margine"])
    b_best = BRAND_EMOJI.get(best["brand"], "🛒")
    embed  = {
        "title":       "📊  Report Opportunità di Rivendita",
        "description": (
            f"🕐  **{ora}**\n"
            f"✅  **{len(risultati)} articoli idonei** su {totale} monitorati\n"
            f"🏆  Migliore: {b_best} **{best['nome']}** → **+€{best['margine']:.2f}**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "color":  0x00C853,
        "fields": fields,
        "footer": {"text": f"🤖 Amazon Price Bot  •  Fonti: Amazon.it · eBay.it · Subito.it"},
    }
    try:
        requests.post(CONFIG["DISCORD_WEBHOOK_URL"], json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        log.error(f"Discord report errore: {e}")

# ══════════════════════════════════════════════════════════════
#  🔄  LOGICA CONTROLLO PREZZI
# ══════════════════════════════════════════════════════════════
async def esegui_controllo():
    ora = datetime.now().strftime("%d/%m/%Y  %H:%M")
    log.info(f"{'═'*60}")
    log.info(f"🔍  Avvio controllo — {ora}")

    prezzi_salvati   = carica_json(PREZZI_FILE)
    storico          = carica_json(STORICO_FILE)
    aggiornamenti    = {}
    risultati_idonei = []

    per_cat = {}
    for a in ARTICOLI:
        per_cat.setdefault(a.get("categoria", "Altro"), []).append(a)

    for categoria, articoli_cat in sorted(per_cat.items()):
        for art in articoli_cat:
            url   = art["url"]
            nome  = art["nome"]
            brand = art.get("brand", "")
            query = art.get("query_rivendita", nome)

            # Prezzo Amazon
            p_amazon, p_str = await asyncio.get_event_loop().run_in_executor(
                None, ottieni_prezzo_amazon, url
            )
            await asyncio.sleep(CONFIG["REQUEST_DELAY"])
            if p_amazon is None:
                continue

            aggiornamenti[url] = p_amazon

            # Prezzo rivendita
            p_riv, fonte = await asyncio.get_event_loop().run_in_executor(
                None, calcola_prezzo_rivendita, query
            )
            await asyncio.sleep(CONFIG["REQUEST_DELAY"])
            if p_riv is None:
                continue

            margine = p_riv - p_amazon
            pct     = (margine / p_riv * 100) if p_riv > 0 else 0

            # Trend
            p_prec = prezzi_salvati.get(url)
            trend  = ""
            if p_prec:
                delta = p_amazon - p_prec
                if delta < 0:
                    trend = f"📉 Sceso di €{abs(delta):.2f}"
                elif delta > 0:
                    trend = f"📈 Salito di €{delta:.2f}"

            if margine >= CONFIG["MIN_RESELL_PROFIT"]:
                risultati_idonei.append({
                    "nome": nome, "brand": brand, "categoria": categoria,
                    "url": url, "prezzo_amazon": p_amazon,
                    "prezzo_rivendita": p_riv, "margine": margine,
                    "pct": pct, "fonte": fonte, "trend": trend,
                })
                storico[url] = {"nome": nome, "margine": margine,
                                "timestamp": datetime.now().isoformat()}
                invia_discord_opportunita(art, p_amazon, p_riv, margine, pct, fonte)
                log.info(f"  ✅ {nome}  →  +€{margine:.2f}")
            else:
                log.info(f"  ❌ {nome}  →  +€{margine:.2f} (insufficiente)")

    prezzi_salvati.update(aggiornamenti)
    salva_json(PREZZI_FILE, prezzi_salvati)
    salva_json(STORICO_FILE, storico)

    # Aggiorna statistiche
    STATO["ultimo_controllo"]    = ora
    STATO["cicli_completati"]   += 1
    STATO["opportunita_trovate"] = len(risultati_idonei)

    invia_report_webhook(risultati_idonei, ora, len(ARTICOLI))
    return risultati_idonei

# ══════════════════════════════════════════════════════════════
#  🤖  BOT DISCORD
# ══════════════════════════════════════════════════════════════
intents = discord.Intents.default()
bot     = commands.Bot(command_prefix="!", intents=intents)
tree    = bot.tree

# ── Task periodico ───────────────────────────────────────────
@tasks.loop(minutes=CONFIG["CHECK_INTERVAL_MINUTES"])
async def ciclo_monitoraggio():
    if STATO["attivo"]:
        log.info("⏱️  Ciclo automatico avviato")
        await esegui_controllo()

# ══════════════════════════════════════════════════════════════
#  📡  SLASH COMMANDS
# ══════════════════════════════════════════════════════════════

@tree.command(name="avvia", description="▶️ Avvia il monitoraggio prezzi Amazon")
async def cmd_avvia(interaction: discord.Interaction):
    if STATO["attivo"]:
        await interaction.response.send_message(
            "⚠️  Il bot è **già attivo**! Usa `/stato` per vedere le info.",
            ephemeral=True
        )
        return
    STATO["attivo"]           = True
    STATO["canale_notifiche"] = interaction.channel_id

    embed = discord.Embed(
        title="▶️  Monitoraggio Avviato!",
        description=(
            f"Il bot controllerà **{len(ARTICOLI)} prodotti** ogni "
            f"**{CONFIG['CHECK_INTERVAL_MINUTES']} minuti**.\n\n"
            f"💰  Margine minimo: **+€{CONFIG['MIN_RESELL_PROFIT']:.0f}**\n"
            f"📡  Fonti: **Amazon.it · eBay.it · Subito.it**\n\n"
            f"Le notifiche arriveranno in questo canale."
        ),
        color=0x00C853
    )
    embed.set_footer(text="🤖 Amazon Price Bot  •  Usa /ferma per interrompere")
    await interaction.response.send_message(embed=embed)
    if not ciclo_monitoraggio.is_running():
        ciclo_monitoraggio.start()
    log.info(f"✅ Bot avviato da {interaction.user}")


@tree.command(name="ferma", description="⏹️ Ferma il monitoraggio prezzi")
async def cmd_ferma(interaction: discord.Interaction):
    if not STATO["attivo"]:
        await interaction.response.send_message(
            "ℹ️  Il bot è già **fermo**.",
            ephemeral=True
        )
        return
    STATO["attivo"] = False
    if ciclo_monitoraggio.is_running():
        ciclo_monitoraggio.cancel()

    embed = discord.Embed(
        title="⏹️  Monitoraggio Fermato",
        description=(
            f"Il bot è stato fermato.\n\n"
            f"📊  Cicli completati: **{STATO['cicli_completati']}**\n"
            f"✅  Opportunità trovate: **{STATO['opportunita_trovate']}**\n\n"
            f"Usa **/avvia** per ripartire."
        ),
        color=0xFF5252
    )
    await interaction.response.send_message(embed=embed)
    log.info(f"⏹️ Bot fermato da {interaction.user}")


@tree.command(name="stato", description="📊 Mostra lo stato attuale del bot")
async def cmd_stato(interaction: discord.Interaction):
    storico = carica_json(STORICO_FILE)
    status_ico   = "🟢 Attivo" if STATO["attivo"] else "🔴 Fermo"
    ultimo       = STATO["ultimo_controllo"] or "Mai eseguito"

    embed = discord.Embed(title="📊  Stato del Bot", color=0x00B4D8)
    embed.add_field(name="⚙️  Stato",             value=status_ico,  inline=True)
    embed.add_field(name="🔍  Ultimo controllo",  value=ultimo,       inline=True)
    embed.add_field(name="🔄  Cicli completati",  value=str(STATO["cicli_completati"]), inline=True)
    embed.add_field(name="📦  Prodotti monitorati", value=str(len(ARTICOLI)), inline=True)
    embed.add_field(name="💰  Margine minimo",    value=f"€{CONFIG['MIN_RESELL_PROFIT']:.0f}", inline=True)
    embed.add_field(name="⏱️  Intervallo",        value=f"{CONFIG['CHECK_INTERVAL_MINUTES']} min", inline=True)
    embed.add_field(name="🏆  Opportunità trovate (storico)", value=str(len(storico)), inline=False)
    embed.set_footer(text="🤖 Amazon Price Bot")
    await interaction.response.send_message(embed=embed)


@tree.command(name="controlla", description="🔍 Forza un controllo immediato di tutti i prezzi")
async def cmd_controlla(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(
        "🔍  Controllo in corso... Potrebbe richiedere alcuni minuti. "
        "Riceverai il report completo nel canale webhook!"
    )
    risultati = await esegui_controllo()
    if risultati:
        await interaction.followup.send(
            f"✅  Controllo completato! Trovate **{len(risultati)} opportunità**. "
            f"Controlla il report qui sopra ☝️"
        )
    else:
        await interaction.followup.send(
            f"😴  Controllo completato. **Nessuna opportunità** con margine ≥ €{CONFIG['MIN_RESELL_PROFIT']:.0f} al momento."
        )
    log.info(f"🔍 Controllo manuale eseguito da {interaction.user}")


@tree.command(name="prodotti", description="📦 Lista tutti i prodotti monitorati per categoria")
async def cmd_prodotti(interaction: discord.Interaction):
    per_cat = {}
    for a in ARTICOLI:
        per_cat.setdefault(a.get("categoria","Altro"), []).append(a)

    embed = discord.Embed(
        title="📦  Prodotti Monitorati",
        description=f"**{len(ARTICOLI)} prodotti totali** divisi per categoria:",
        color=0x7289DA
    )
    for cat, items in sorted(per_cat.items()):
        c_ico = CAT_EMOJI.get(cat, "📦")
        nomi  = "\n".join(
            f"{BRAND_EMOJI.get(a['brand'],'🛒')} {a['nome']}" for a in items
        )
        embed.add_field(
            name=f"{c_ico}  {cat}  ({len(items)})",
            value=nomi,
            inline=True
        )
    embed.set_footer(text=f"🤖 Amazon Price Bot  •  Margine minimo: €{CONFIG['MIN_RESELL_PROFIT']:.0f}")
    await interaction.response.send_message(embed=embed)


# ══════════════════════════════════════════════════════════════
#  🚀  ON READY
# ══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"📦 {len(ARTICOLI)} prodotti Amazon"
        )
    )
    log.info(f"{'═'*60}")
    log.info(f"🤖  Bot online come: {bot.user}")
    log.info(f"📦  Prodotti monitorati: {len(ARTICOLI)}")
    log.info(f"💰  Margine minimo: +€{CONFIG['MIN_RESELL_PROFIT']:.0f}")
    log.info(f"⏱️  Intervallo: {CONFIG['CHECK_INTERVAL_MINUTES']} min")
    log.info(f"{'═'*60}")
    log.info("✅  Slash commands sincronizzati. Usa /avvia per partire!")

# ══════════════════════════════════════════════════════════════
#  🚀  MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║     🤖  AMAZON RESELLING BOT  —  Discord Slash Commands      ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    print("  Avvio bot Discord...")
    print("  Comandi disponibili su Discord:")
    print("    /avvia      ▶️  Avvia il monitoraggio")
    print("    /ferma      ⏹️  Ferma il monitoraggio")
    print("    /stato      📊  Stato e statistiche")
    print("    /controlla  🔍  Controllo immediato")
    print("    /prodotti   📦  Lista prodotti monitorati\n")
    bot.run(CONFIG["DISCORD_BOT_TOKEN"])
