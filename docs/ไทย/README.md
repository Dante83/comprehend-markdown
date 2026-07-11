# comprehend-markdown

*เพียงสัมผัสคัมภีร์และร่ายมนตรา... เพียงไม่กี่นาทีหรือหนึ่งชั่วโมง (ขึ้นอยู่กับความหนาของคัมภีร์) คุณก็จะเข้าใจเนื้อหาใน Markdown ทุกภาษา*

เซิร์ฟเวอร์ MCP สำหรับแปลไฟล์ `README.md` ของโปรเจกต์เป็นภาษาต่างๆ พร้อมไปป์ไลน์แบบ standalone ที่ทำงานด้วยลูปผู้เขียนและผู้ตรวจทาน (writer/reviewer loop) โดยใช้โมเดลจาก LM Studio ในเครื่อง

คุณสามารถกำหนดค่าทั้งภาษาต้นทางและภาษาปลายทางได้ โดยมีภาษาอังกฤษเป็นค่าเริ่มต้น คุณสามารถตั้งค่า `source_language` เพื่อแปล *ออกจาก* ภาษาจีน อินโดนีเซีย หรือภาษาอื่นๆ และตั้งค่า `target_languages` เพื่อเลือกภาษาที่ต้องการให้กระจายออกไป (ดูรายละเอียดที่ [การเลือกภาษาต้นทางและปลายทาง](#การเลือกภาษาต้นทางและปลายทาง))

สำหรับโปรเจกต์เป้าหมาย ระบบจะคาดหวัง (และสร้างให้หากจำเป็น) โครงสร้างดังนี้:

```
<project-root>/docs/<source>/README.md  ต้นฉบับหลัก (ค่าเริ่มต้นเป็นภาษาอังกฤษ)
<project-root>/docs/<lang>/README.md    เวอร์ชันที่แปลแล้ว แยกตามแต่ละภาษา
<project-root>/README.md                หน้าแลนดิ้งเพจสำหรับเลือกภาษา (สร้างโดยอัตโนมัติ)
```

หากโปรเจกต์ยังไม่ได้ย้ายโครงสร้าง (ไฟล์ต้นฉบับยังอยู่ที่ root) ระบบก็ยังทำงานได้ โดยจะใช้ `README.md` ที่ root เป็นต้นฉบับ และเมื่อรัน `pipeline` จนเสร็จสิ้น ไฟล์ดังกล่าวจะถูกย้ายไปที่ `docs/<source>/` (เช่น `docs/English/`) และถูกแทนที่ด้วยหน้าแลนดิ้งเพจสั้นๆ ที่รวมลิงก์ไปยังคำแปลทุกภาษาที่มี

## การติดตั้ง (Setup)

ทุกขั้นตอน (การสร้าง venv, การติดตั้ง/ซิงค์ dependency) ถูกจัดการโดย `run.sh` จึงไม่มีขั้นตอนการติดตั้งแยกต่างหาก ระบบจะอ่านแพ็กเกจจาก `requirements.txt` และติดตั้งใหม่ทุกครั้งที่รัน ดังนั้นหากมีการอัปเดต dependency เพียงแค่รันสคริปต์นี้อีกครั้ง

หากคุณต้องการใช้โมเดลใน LM Studio ตัวอื่นนอกเหนือจากค่าเริ่มต้น ให้แก้ไขค่าใน `config.json`

### การเลือกภาษาต้นทางและปลายทาง

มีคีย์การตั้งค่าสองตัวใน `config.json` ที่ควบคุมทิศทางการแปล:

- **`source_language`** — ภาษาที่ใช้เขียน `README.md` ต้นฉบับ และเป็นชื่อโฟลเดอร์ `docs/<source_language>/` ค่าเริ่มต้นคือ `English` คุณสามารถเปลี่ยนเป็น `中文`, `Indonesia` หรือภาษาอื่นๆ เพื่อแปล *ออกจาก* ภาษานั้นๆ
- **`target_languages`** — รายการภาษาที่ไปป์ไลน์จะแปล *ไปเป็น* หากมีรายการใดตรงกับ `source_language` ระบบจะข้ามภาษานั้นโดยอัตโนมัติ ดังนั้นการใส่ภาษาต้นทางไว้ในรายการนี้จึงไม่มีผลเสียใดๆ

ตัวอย่างเช่น หากต้องการแปล README ภาษาจีน เป็นภาษาอังกฤษและสเปน:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

หากไม่ได้ระบุ `target_languages` ไปป์ไลน์จะใช้รายการภาษามาตรฐาน 18 ภาษาที่มีมาให้ในตัว

ค่า `api_key` จะมีความสำคัญก็ต่อเมื่อคุณเปิดใช้งาน "Require API Key" ในการตั้งค่า Developer server ของ LM Studio มิฉะนั้นให้ปล่อยไว้เป็น `"lm-studio"` ซึ่ง LM Studio จะเพิกเฉยต่อค่านี้ โปรดทราบว่าส่วนนี้ใช้กับโหมด `pipeline` เท่านั้น เนื่องจากเป็นส่วนเดียวที่เรียกใช้ OpenAI-compatible endpoint ของ LM Studio โดยตรง ส่วนโหมด `serve` จะไม่คุยกับ API ของ LM Studio เพราะตัว LM Studio เองนั่นแหละที่เป็น MCP client ที่เรียกใช้งานเซิร์ฟเวอร์นี้

คุณสามารถตั้งค่า `max_tokens` ได้ที่นี่ แต่ไม่แน่ใจว่า LM Studio รองรับค่านี้จริงหรือไม่ โปรดตรวจสอบให้แน่ใจว่าได้ตั้งค่านี้ในตัวโมเดลให้มีค่าอย่างน้อยประมาณ 24576 ก่อนเริ่มรันสคริปต์

## การใช้งาน (Usage)

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP server
./run.sh pipeline /absolute/path/to/project   # รัน main.py แบบ end-to-end
```

ทั้งสองโหมดต้องการ **เส้นทางแบบ absolute (absolute path)** ไปยังโฟลเดอร์โปรเจกต์ที่มีไฟล์ `README.md` ที่ต้องการแปล ในโหมด `pipeline` คุณสามารถละเว้นเส้นทางไว้เพื่อให้ระบบถามในภายหลังได้ หากคุณรันผ่านเทอร์มินัลแบบ interactive:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(โหมด `serve` จะไม่มีการถามข้อมูล เนื่องจากเมื่อเริ่มทำงาน stdin/stdout จะกลายเป็นช่องทาง MCP JSON-RPC และ MCP host จะเรียกใช้งานแบบ non-interactively อยู่แล้ว)

### `serve` — ในฐานะเครื่องมือของ MCP host

นี่คือส่วนที่ MCP host (เช่น LM Studio) ควรชี้คำสั่ง `command` มาที่นี่ โดยระบุ absolute path ของโปรเจกต์เป้าหมายเป็น argument คงที่ ซึ่งจะเปิดให้ใช้งาน:

- **tool** `write_readme(language, content)` — เขียนไฟล์ `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — เขียนไฟล์ `README.md` ที่ root (หน้าเลือกภาษา)
- **resource** `docs://readme` — ไฟล์ต้นฉบับ (`docs/<source_language>/README.md` หรือ fallback ไปที่ root `README.md`)
- **resource** `docs://readme/{language}` — คำแปลที่มีอยู่ (ถ้ามี)
- **resource** `docs://dir_readme` — ไฟล์ `README.md` ที่ root
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — ลูปสำหรับการแปลใหม่
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — เส้นทางการอัปเดต: เปรียบเทียบคำแปลเดิมกับต้นฉบับปัจจุบันและแก้ไขเฉพาะจุดที่จำเป็น
- **prompt** `create_docs_language_directory` — สร้างหน้าเลือกภาษาที่ root จากรายการคำแปลที่มีอยู่

โมเดลของตัว host เองจะเป็นผู้ขับเคลื่อนการเรียกใช้ tool ส่วนเซิร์ฟเวอร์นี้ทำหน้าที่จัดการ I/O ของไฟล์และเตรียม prompt templates เท่านั้น

#### การเพิ่มเข้าไปใน LM Studio

การตั้งค่า MCP ของ LM Studio อยู่ที่ `~/.lmstudio/mcp.json` ให้เพิ่มรายการดังนี้:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/absolute/path/to/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/absolute/path/to/the/project/you/want/to/translate"
      ]
    }
  }
}
```

ค่า `args` ตัวที่สองจะถูกกำหนดตายตัวตอนเชื่อมต่อ เนื่องจาก config ของ LM Studio เป็น JSON แบบ static และไม่รองรับ interactive prompt ดังนั้นต้องระบุเส้นทางจริงของโปรเจกต์ที่คุณต้องการแปล ไม่ใช่เส้นทางของ repo นี้ (เว้นแต่คุณต้องการแปล README ของ repo นี้เอง)