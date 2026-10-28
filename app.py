import os
import re
import json
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TIMEOUT = 30
GEMINI_TIMEOUT = 90

HEADERS = {
    "User-Agent": "GeneProteinDiseaseStudentProject/1.0 (educational use)"
}
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return jsonify({
            "error": "ไม่พบ GEMINI_API_KEY กรุณาตรวจสอบไฟล์ .env"
        }), 503

    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return jsonify({"error": "รูปแบบข้อมูลคำขอไม่ถูกต้อง"}), 400

    gene = data.get("gene") or {}
    proteins = data.get("proteins") or []
    articles = data.get("articles") or []
    disease = str(data.get("disease") or "ไม่ได้ระบุ")[:120]

    if not isinstance(gene, dict) or not gene.get("symbol"):
        return jsonify({
            "error": "กรุณาค้นหายีนก่อนสร้างบทสรุป"
        }), 400

    if not isinstance(proteins, list) or not isinstance(articles, list):
        return jsonify({
            "error": "รูปแบบข้อมูลโปรตีนหรือบทความไม่ถูกต้อง"
        }), 400

    
    
    evidence = {
        "gene": gene,
        "proteins": proteins[:3],
        "pubmed_articles": articles[:3]
    }



    
    prompt = (
        "คุณเป็นผู้ช่วยด้านชีวสารสนเทศเพื่อการศึกษา "
        "สรุปเป็นภาษาไทยไม่เกิน 120 คำ "
        "ใช้เฉพาะหลักฐานใน JSON ห้ามแต่งข้อมูลเพิ่ม\n\n"
        "ตอบ 4 หัวข้อแบบสั้น:\n"
        "1. ยีนและ Gene ID\n"
        "2. โปรตีนและหน้าที่\n"
        "3. บทความที่เกี่ยวข้อง\n"
        "4. ข้อจำกัดและแหล่งอ้างอิง\n\n"
        "ห้ามสรุปว่ามีความสัมพันธ์เชิงสาเหตุหากหลักฐานไม่เพียงพอ "
        "ปิดท้ายว่า ข้อมูลนี้ไม่ใช่คำแนะนำทางการแพทย์\n\n"
        "หลักฐาน JSON:\n"
        + json.dumps(evidence, ensure_ascii=False)
    )


    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    if model.startswith("models/"):
        model = model[len("models/"):]

    if not model or any(ch in model for ch in " /?#\n\r"):
        return jsonify({
            "error": "ชื่อ GEMINI_MODEL ในไฟล์ .env ไม่ถูกต้อง"
        }), 400

    # URL ต้องเป็น URL จริง ห้ามใส่ Markdown link
    
    url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{model}:generateContent"
)

    request_body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024
        }
    }

    try:
        response = requests.post(
        url,
        params={"key": api_key},
        json=request_body,
        headers=HEADERS,
        timeout=(15, 120)
    )

        if not response.ok:
            try:
                error_data = response.json()
                detail = error_data.get("error", {}).get(
                    "message", "ไม่มีรายละเอียด"
                )
            except (ValueError, AttributeError):
                detail = "ไม่สามารถอ่านรายละเอียดข้อผิดพลาดได้"

            detail = str(detail).replace(api_key, "[REDACTED]")
            status = response.status_code

            app.logger.error(
                "Gemini API error: HTTP %s, model=%s, detail=%s",
                status, model, detail
            )

            if status == 400:
                message = f"คำขอ Gemini ไม่ถูกต้อง: {detail}"
            elif status in (401, 403):
                message = (
                    "Gemini ปฏิเสธการเข้าถึง กรุณาตรวจสอบ API Key "
                    "และสิทธิ์การใช้งาน"
                )
            elif status == 404:
                message = (
                    f"ไม่พบหรือไม่สามารถใช้โมเดล '{model}' ได้ "
                    "กรุณาตรวจสอบชื่อโมเดลใน Google AI Studio"
                )
            elif status == 429:
                message = (
                    "Gemini ใช้โควตาครบหรือมีคำขอมากเกินไป "
                    "กรุณาลองใหม่ภายหลัง"
                )
            elif status >= 500:
                message = "Gemini API ขัดข้องชั่วคราว กรุณาลองใหม่"
            else:
                message = f"Gemini API HTTP {status}: {detail}"

            return jsonify({"error": message}), 502

        result = response.json()
        candidates = result.get("candidates", [])

        if not candidates:
            return jsonify({
                "error": "Gemini ไม่ส่งบทสรุปกลับมา กรุณาลองใหม่"
            }), 502

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason", "")
        parts = candidate.get("content", {}).get("parts", [])

        summary = "\n".join(
            part["text"]
            for part in parts
            if isinstance(part, dict)
            and isinstance(part.get("text"), str)
        ).strip()

        if not summary:
            return jsonify({
                "error": (
                    "Gemini ไม่ได้ส่งข้อความสรุปกลับมา "
                    f"(finish reason: {finish_reason or 'ไม่ระบุ'})"
                )
            }), 502

        

        if finish_reason == "MAX_TOKENS":
            app.logger.warning(
                "Gemini output truncated: model=%s, finish_reason=%s",
                model,
                finish_reason
            )
            return jsonify({
                "error": (
                    "Gemini สร้างบทสรุปไม่ครบ "
                    "กรุณาลองอีกครั้ง"
                )
            }), 502

        summary = re.sub(r"\n{3,}", "\n\n", summary).strip()

        return jsonify({
            "summary": summary,
            "model": model,
            "notice": (
                "บทสรุปสร้างจากข้อมูลที่ค้นพบและอาจมีข้อผิดพลาด "
                "โปรดตรวจสอบแหล่งอ้างอิงต้นฉบับ "
                "ไม่ใช้เพื่อการวินิจฉัยโรคหรือการรักษา"
            )
        }), 200


    except requests.Timeout:
        app.logger.exception(
            "Gemini API timeout; model=%s; url=%s",
            model,
            url
        )
        return jsonify({
            "error": (
                "Gemini ใช้เวลาตอบเกิน 120 วินาที "
                "กรุณาตรวจสอบอินเทอร์เน็ตและลองใหม่"
            )
        }), 504
# ===== Gene / Protein / PubMed Search API =====

from flask import jsonify, request
import xml.etree.ElementTree as ET


def search_gene(symbol):
    """Search human genes using NCBI Gene."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "gene",
        "term": f"{symbol}[Gene Name] AND Homo sapiens[Organism]",
        "retmode": "json",
        "retmax": 1
    }

    response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    ids = response.json().get("esearchresult", {}).get("idlist", [])

    if not ids:
        return None

    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    summary_response = requests.get(
        summary_url,
        params={"db": "gene", "id": ids[0], "retmode": "json"},
        headers=HEADERS,
        timeout=TIMEOUT
    )
    summary_response.raise_for_status()

    result = summary_response.json().get("result", {})
    item = result.get(ids[0], {})

    return {
        "symbol": item.get("name", symbol),
        "id": ids[0],
        "description": item.get("description", ""),
        "organism": item.get("organism", {}).get("scientificname", "Homo sapiens"),
        "url": f"https://www.ncbi.nlm.nih.gov/gene/{ids[0]}"
    }


def search_uniprot(symbol):
    """Search UniProt for proteins associated with a human gene."""
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": f"(gene:{symbol}) AND (organism_id:9606)",
        "format": "json",
        "size": 5,
        "fields": "accession,protein_name,gene_names,cc_function"
    }

    response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    proteins = []
    for item in response.json().get("results", []):
        accession = item.get("primaryAccession", "")
        protein_desc = (
            item.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value", "")
        )

        functions = []
        for comment in item.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                for text_item in comment.get("texts", []):
                    value = text_item.get("value", "")
                    if value:
                        functions.append(value)

        proteins.append({
            "name": protein_desc or accession,
            "accession": accession,
            "function": " ".join(functions),
            "url": f"https://www.uniprot.org/uniprotkb/{accession}"
        })

    return proteins


def search_pubmed(symbol, disease):
    """Search PubMed for articles matching the gene and disease keywords."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    term = f'("{symbol}"[Title/Abstract])'
    if disease:
        term += f' AND ("{disease}"[Title/Abstract])'

    response = requests.get(
        url,
        params={"db": "pubmed", "term": term, "retmode": "json", "retmax": 5},
        headers=HEADERS,
        timeout=TIMEOUT
    )
    response.raise_for_status()
    ids = response.json().get("esearchresult", {}).get("idlist", [])

    if not ids:
        return []

    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_response = requests.get(
        fetch_url,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        headers=HEADERS,
        timeout=TIMEOUT
    )
    fetch_response.raise_for_status()

    root = ET.fromstring(fetch_response.text)
    articles = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="")
        title_node = article.find(".//ArticleTitle")
        title = "".join(title_node.itertext()).strip() if title_node is not None else ""

        journal = article.findtext(".//Journal/Title", default="")
        year = (
            article.findtext(".//PubDate/Year")
            or article.findtext(".//PubDate/MedlineDate", default="")
        )

        articles.append({
            "title": title,
            "journal": journal,
            "year": year[:4] if year else "",
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        })

    return articles


@app.route("/api/search", methods=["GET"])
def api_search():
    symbol = request.args.get("gene", "").strip()
    disease = request.args.get("disease", "").strip()

    if not symbol:
        return jsonify({"error": "Please enter a gene symbol."}), 400

    if len(symbol) > 80 or len(disease) > 120:
        return jsonify({"error": "Search keywords are too long."}), 400

    try:
        gene = search_gene(symbol)
        if not gene:
            return jsonify({"error": f"No human gene found for '{symbol}'."}), 404

        proteins = search_uniprot(gene["symbol"])
        articles = search_pubmed(gene["symbol"], disease)

        return jsonify({
            "gene": gene,
            "proteins": proteins,
            "articles": articles,
            "disease_query": disease
        })

    except requests.Timeout:
        app.logger.exception("Search API timeout")
        return jsonify({"error": "External database request timed out. Please try again."}), 504

    except requests.RequestException:
        app.logger.exception("Gemini API request failed")
        return jsonify({
            "error": "Gemini API เรียกใช้งานไม่สำเร็จ กรุณาตรวจสอบ Terminal"
        }), 502

    except (ValueError, ET.ParseError):
        app.logger.exception("Could not parse external database response")
        return jsonify({"error": "Could not read the database response."}), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
