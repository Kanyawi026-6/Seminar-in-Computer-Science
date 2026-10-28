# Gene–Protein–Disease Explorer

เว็บต้นแบบสำหรับการเรียนรู้ชีวสารสนเทศ ค้นข้อมูลยีนมนุษย์ โปรตีน บทความที่ตรงกับคำค้นโรค และสรุปข้อมูลด้วย Gemini เมื่อผู้ใช้กำหนด API key

## คุณสมบัติ
- ค้นหายีนมนุษย์จาก NCBI Gene และแสดง Gene ID / คำอธิบาย / ลิงก์ต้นทาง
- ค้นหา annotation โปรตีนจาก UniProt REST API
- ค้นหาบทความ PubMed ด้วย Gene symbol และ Disease keyword (ถ้าระบุ)
- กราฟเครือข่ายแสดงยีนและโปรตีนที่พบ
- ปุ่ม AI Summary ใช้ Gemini API สรุปจากข้อมูลที่ค้นพบ โดยพยายามจำกัดการสร้างข้อมูลให้อยู่ในหลักฐานที่ส่งให้
- ข้อความแจ้งข้อจำกัดและลิงก์แหล่งข้อมูลต้นฉบับ

## สิ่งที่ต้องมี
- Python 3.10+
- อินเทอร์เน็ต
- (ไม่บังคับ) Gemini API key เพื่อเปิดใช้ AI Summary

## เริ่มระบบบน Windows PowerShell
เปิด Terminal ในโฟลเดอร์โปรเจกต์ แล้วรัน:
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```
เปิด http://127.0.0.1:5000 ในเบราว์เซอร์ หากสร้าง `.venv` และติดตั้งแพ็กเกจไปแล้ว ไม่ต้องทำซ้ำทั้งหมด สามารถ activate แล้วรัน `python app.py` ได้

## ตั้งค่า Gemini API (ไม่บังคับ)
1. สร้าง/คัดลอก API key จาก Google AI Studio ด้วยบัญชีของตนเอง และตรวจสอบเงื่อนไข/โควตาการใช้งานก่อน
2. อย่าใส่ API key ลงในไฟล์ Python, HTML, Git หรือรายงาน และอย่าแชร์ key ให้ผู้อื่น
3. ใน PowerShell หน้าต่างเดียวกับที่จะรันเซิร์ฟเวอร์ ตั้งค่าแบบชั่วคราว:
```powershell
$env:GEMINI_API_KEY="วาง_API_KEY_ของคุณตรงนี้"
$env:GEMINI_MODEL="gemini-2.5-flash"
python app.py
```
หากเซิร์ฟเวอร์กำลังรันอยู่ ให้กด `Ctrl+C` ก่อนตั้งค่า แล้วรันใหม่ในหน้าต่างเดิม หากไม่ตั้งค่า API key การค้นหา NCBI/UniProt/PubMed ยังทำงานได้ แต่ปุ่ม AI จะบอกวิธีตั้งค่าแทนการสร้างบทสรุป

## ทดสอบระบบ
1. ค้นหา `TP53` แล้วตรวจว่ามี Gene ID และลิงก์ NCBI
2. ตรวจรายการโปรตีนและลิงก์ UniProt
3. ใส่ Disease keyword เช่น `breast cancer` แล้วค้นหาอีกครั้ง ตรวจบทความและ PMID จาก PubMed
4. ตรวจกราฟ gene-protein
5. ตั้ง Gemini API key แล้วกดสร้างบทสรุป (ถ้ามี key)
6. ทดสอบ `BRCA1` และ `EGFR` เพิ่มเติม พร้อมจดผลจริงและ error ที่พบ

## ข้อจำกัดสำคัญ
- Disease keyword ใช้กรองบทความใน PubMed เท่านั้น ไม่ได้ยืนยันความสัมพันธ์เชิงสาเหตุระหว่างยีนกับโรค และระบบยังไม่ได้เชื่อมฐานข้อมูลโรคเฉพาะทางเพื่อยืนยัน disease-gene association
- กราฟปัจจุบันเชื่อมยีนกับรายการโปรตีนที่ UniProt ส่งกลับ ไม่ใช่หลักฐานทดลองของ interaction
- AI summary เป็นข้อความที่สร้างโดยโมเดล จึงต้องตรวจสอบกับแหล่งต้นฉบับทุกครั้ง ไม่ควรนำไปใช้วินิจฉัย ประเมินความเสี่ยง หรือให้คำแนะนำทางการแพทย์
- ไม่มีฐานข้อมูลในเครื่อง ข้อมูลดึงสดจากบริการภายนอก และอาจช้าหรือไม่พร้อมใช้งาน
- การประเมินผู้ใช้/ความพึงพอใจต้องเก็บข้อมูลจริงก่อนรายงานผล

## แหล่งข้อมูล
- NCBI E-utilities: https://eutilities.github.io/site/
- PubMed: https://pubmed.ncbi.nlm.nih.gov/
- UniProt REST API: https://www.uniprot.org/help/api
- Google AI Studio: https://aistudio.google.com/
