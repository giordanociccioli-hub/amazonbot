"""
💳  LINK DI PAGAMENTO STRIPE
Crea 3 Payment Link Stripe (uno per piano) per l'accesso premium al bot.
Rieseguirlo non crea duplicati: riusa prodotto, prezzi e link già esistenti.

USO:
    export STRIPE_SECRET_KEY=sk_test_...   # oppure sk_live_...
    python stripe_links.py
"""

import os, sys, logging
import requests

log = logging.getLogger("AmazonBot")

STRIPE_API    = "https://api.stripe.com/v1"
PRODOTTO_ID   = "amazonbot_premium"
PRODOTTO_NOME = "Amazon Reselling Bot — Accesso Premium"

# Importi in centesimi di euro: modifica qui nome, prezzo e durata dei 3 piani.
# Se cambi un prezzo, al prossimo avvio viene creato un nuovo link e il vecchio disattivato.
PIANI_STRIPE = [
    {"chiave": "settimanale", "nome": "Settimanale", "importo": 499,  "intervallo": "week"},
    {"chiave": "mensile",     "nome": "Mensile",     "importo": 1499, "intervallo": "month"},
    {"chiave": "annuale",     "nome": "Annuale",     "importo": 9999, "intervallo": "year"},
]

INTERVALLI = {"week": "settimana", "month": "mese", "year": "anno"}


class StripeErrore(RuntimeError):
    def __init__(self, status, messaggio):
        super().__init__(f"Stripe {status}: {messaggio}")
        self.status = status


def _stripe(metodo, percorso, **dati):
    chiave = os.environ.get("STRIPE_SECRET_KEY")
    if not chiave:
        raise RuntimeError("STRIPE_SECRET_KEY non impostata")
    campo = "params" if metodo == "GET" else "data"
    r = requests.request(metodo, f"{STRIPE_API}{percorso}", auth=(chiave, ""),
                         timeout=20, **{campo: dati})
    try:
        body = r.json()
    except ValueError:
        body = {}
    if not r.ok:
        raise StripeErrore(r.status_code, body.get("error", {}).get("message") or r.text[:200])
    return body


def _assicura_prodotto():
    try:
        prodotto = _stripe("GET", f"/products/{PRODOTTO_ID}")
    except StripeErrore as e:
        if e.status != 404:
            raise
        return _stripe("POST", "/products", id=PRODOTTO_ID, name=PRODOTTO_NOME)
    if not prodotto["active"]:
        prodotto = _stripe("POST", f"/products/{PRODOTTO_ID}", active="true")
    return prodotto


def _assicura_prezzo(piano):
    lookup  = f"{PRODOTTO_ID}_{piano['chiave']}_{piano['importo']}_{piano['intervallo']}"
    trovati = _stripe("GET", "/prices", **{"lookup_keys[]": lookup, "active": "true"})["data"]
    if trovati:
        return trovati[0]
    return _stripe("POST", "/prices", **{
        "product": PRODOTTO_ID, "currency": "eur", "unit_amount": piano["importo"],
        "recurring[interval]": piano["intervallo"], "lookup_key": lookup, "nickname": piano["nome"],
    })


def _link_attivi():
    links, dopo = [], None
    while True:
        params = {"active": "true", "limit": 100}
        if dopo:
            params["starting_after"] = dopo
        pagina = _stripe("GET", "/payment_links", **params)
        links += pagina["data"]
        if not pagina["has_more"]:
            return links
        dopo = pagina["data"][-1]["id"]


def prezzo_leggibile(piano):
    return f"€{piano['importo'] / 100:.2f}/{INTERVALLI[piano['intervallo']]}"


def crea_link_stripe():
    """Restituisce i PIANI_STRIPE arricchiti con l'"url" del rispettivo Payment Link."""
    _assicura_prodotto()
    attivi    = _link_attivi()
    risultato = []
    for piano in PIANI_STRIPE:
        prezzo = _assicura_prezzo(piano)
        link   = None
        for pl in attivi:
            meta = pl.get("metadata", {})
            if meta.get("bot_piano") != piano["chiave"]:
                continue
            if link is None and meta.get("bot_prezzo") == prezzo["id"]:
                link = pl
            else:
                # Prezzo cambiato (o duplicato): il vecchio link non deve restare acquistabile
                _stripe("POST", f"/payment_links/{pl['id']}", active="false")
                log.info(f"💳 Disattivato vecchio link {piano['nome']}: {pl['url']}")
        if link is None:
            link = _stripe("POST", "/payment_links", **{
                "line_items[0][price]":    prezzo["id"],
                "line_items[0][quantity]": 1,
                "metadata[bot_piano]":     piano["chiave"],
                "metadata[bot_prezzo]":    prezzo["id"],
            })
            log.info(f"💳 Creato link {piano['nome']}: {link['url']}")
        risultato.append({**piano, "url": link["url"]})
    return risultato


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        links = crea_link_stripe()
    except (RuntimeError, requests.RequestException) as e:
        sys.exit(f"❌ {e}")
    righe = [f"- **{l['nome']}** ({prezzo_leggibile(l)}): {l['url']}" for l in links]
    print("\n".join(righe))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## 💳 Link di pagamento Stripe\n\n" + "\n".join(righe) + "\n")
