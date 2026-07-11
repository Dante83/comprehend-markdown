# comprehend-markdown

*Bạn chạm tay vào cuộn giấy và đọc lời chú. Vài phút hoặc một giờ sau (tùy thuộc vào độ dày của cuộn giấy), bạn sẽ thấu hiểu nội dung Markdown bằng bất kỳ ngôn ngữ nào.*

Một MCP server giúp dịch tệp `README.md` của dự án sang các ngôn ngữ khác, đi kèm với một pipeline độc lập chạy vòng lặp người viết/người hiệu đính (writer/reviewer loop) sử dụng mô hình LM Studio cục bộ.

Ngôn ngữ nguồn và ngôn ngữ đích đều có thể cấu hình được — tiếng Anh chỉ là mặc định. Hãy thiết lập `source_language` để dịch *từ* tiếng Trung, tiếng Indonesia hoặc bất kỳ ngôn ngữ nào khác, và `target_languages` để chọn các ngôn ngữ muốn dịch sang (xem [Chọn ngôn ngữ nguồn và đích](#chọn-ngôn ngữ-nguồn-và-đích)).

Đối với bất kỳ dự án mục tiêu nào, công cụ này yêu cầu (và sẽ tự tạo nếu cần):

```
<project-root>/docs/<source>/README.md  bản gốc chuẩn (mặc định là tiếng Anh)
<project-root>/docs/<lang>/README.md    các bản dịch, mỗi ngôn ngữ một tệp
<project-root>/README.md                trang đích chọn ngôn ngữ (được tự động tạo)
```

Những dự án chưa được di chuyển — bản gốc vẫn nằm ở thư mục gốc — cũng hoạt động bình thường: tệp `README.md` ở gốc sẽ được dùng làm nguồn, và khi kết thúc quá trình chạy `pipeline`, nó sẽ được chuyển vào `docs/<source>/` (ví dụ: `docs/English/`) và được thay thế bằng một trang đích ngắn gọn chứa liên kết đến tất cả các bản dịch hiện có.

## Setup

Mọi thứ (tạo venv, cài đặt/đồng bộ hóa phụ thuộc) đều được xử lý bởi `run.sh` — không cần bước cài đặt riêng biệt. Nó đọc các gói từ `requirements.txt` và cài đặt lại mỗi khi chạy, vì vậy để cập nhật các phụ thuộc mới, bạn chỉ cần chạy lại lệnh này.

Nếu bạn muốn trỏ đến một mô hình LM Studio cục bộ khác với mặc định, hãy sao chép tệp cấu hình mẫu và chỉnh sửa nó:

```bash
cp config.local.json.example config.local.json
```

Tệp `config.local.json` được gitignore và sẽ ghi đè lên các khóa trong `config.json`, vì vậy bạn có thể tùy chỉnh `lm_studio_url` / `model_name` / `api_key` cục bộ mà không làm ảnh hưởng đến các giá trị mặc định đã commit.

### Chọn ngôn ngữ nguồn và đích

Hai khóa cấu hình điều khiển hướng dịch, cả server và pipeline đều đọc chúng (từ `config.py`), nên chúng sẽ luôn đồng nhất:

- **`source_language`** — ngôn ngữ mà tệp `README.md` chuẩn được viết, và là tên của thư mục `docs/<source_language>/`. Mặc định là `"English"`. Hãy đặt thành `"中文"`, `"Bahasa Indonesia"`, hoặc bất kỳ ngôn ngữ nào khác để dịch *từ* ngôn ngữ đó.
- **`target_languages`** — danh sách các ngôn ngữ mà pipeline sẽ dịch *sang*. Bất kỳ mục nào trùng với `source_language` sẽ tự động bị bỏ qua, nên việc để ngôn ngữ nguồn trong danh sách này là vô hại.

Ví dụ, để dịch một README tiếng Trung sang tiếng Anh và tiếng Tây Ban Nha:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Nếu `target_languages` bị bỏ trống, pipeline sẽ quay về danh sách 18 ngôn ngữ tích hợp sẵn.

`api_key` chỉ quan trọng nếu bạn bật "Require API Key" trong cài đặt Developer server của LM Studio — nếu không, hãy để mặc định là `"lm-studio"`, giá trị mà LM Studio sẽ bỏ qua. Lưu ý rằng điều này chỉ áp dụng cho chế độ `pipeline`, vì đây là phần duy nhất gọi trực tiếp đến endpoint tương thích OpenAI của LM Studio; chế độ `serve` không bao giờ giao tiếp với API của LM Studio vì chính LM Studio mới là MCP client gọi vào server này.

## Usage

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP server
./run.sh pipeline /absolute/path/to/project   # chạy main.py end-to-end
```

Cả hai chế độ đều yêu cầu **đường dẫn tuyệt đối** đến thư mục dự án chứa tệp `README.md` cần dịch. Trong chế độ `pipeline`, bạn có thể bỏ qua đường dẫn này và nhập sau khi được nhắc, miễn là bạn đang chạy tương tác trong terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(Chế độ `serve` không bao giờ yêu cầu nhập liệu — một khi khởi động, stdin/stdout sẽ trở thành kênh JSON-RPC của MCP, và các MCP host cũng khởi chạy nó ở chế độ không tương tác.)

### `serve` — dưới dạng công cụ cho MCP host

Đây là lệnh mà một MCP host (ví dụ: LM Studio) nên trỏ đến trong phần cấu hình server `command`, với đường dẫn tuyệt đối của dự án mục tiêu làm đối số cố định. Nó cung cấp:

- **tool** `write_readme(language, content)` — ghi tệp `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — ghi tệp `README.md` ở gốc (trang đích chọn ngôn ngữ)
- **resource** `docs://readme` — bản nguồn (`docs/<source_language>/README.md`, hoặc quay về `README.md` ở gốc nếu không tìm thấy)
- **resource** `docs://readme/{language}` — bản dịch hiện có, nếu có
- **resource** `docs://dir_readme` — tệp `README.md` ở gốc
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — vòng lặp dịch mới
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — quy trình cập nhật: so sánh bản dịch hiện có với bản nguồn hiện tại và vá lỗi với những thay đổi tối thiểu
- **prompt** `create_docs_language_directory` — xây dựng trang chọn ngôn ngữ ở gốc từ danh sách các bản dịch hiện có

Mô hình của chính host sẽ điều khiển việc gọi tool; server này chỉ cung cấp I/O tệp và các mẫu prompt.

#### Thêm vào LM Studio

Cấu hình MCP của LM Studio nằm tại `~/.lmstudio/mcp.json`. Hãy thêm một mục như sau:

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

Đối số `args` thứ hai được cố định tại thời điểm kết nối — cấu hình của LM Studio là JSON tĩnh và không hỗ trợ nhập liệu tương tác, vì vậy đó phải là đường dẫn thực tế mà bạn muốn dịch, chứ không phải đường dẫn của repo này (trừ khi bạn muốn dịch chính repo này).

### `pipeline` — độc lập, không cần MCP host

Tự chạy toàn bộ vòng lặp dịch $\rightarrow$ phê bình $\rightarrow$ chỉnh sửa cho các `target_languages` đã cấu hình (danh sách mặc định 18 ngôn ngữ: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — xem [Chọn ngôn ngữ nguồn và đích](#chọn-ngôn ngữ-nguồn-và-đích) để thay đổi danh sách hoặc ngôn ngữ nguồn), gọi trực tiếp endpoint tương thích OpenAI của LM Studio cho các lượt viết/hiệu đính và khởi tạo một bản sao nội bộ của `server.py` qua stdio để thực hiện I/O tệp. Hữu ích cho việc dịch hàng loạt mà không cần thông qua giao diện người dùng của LM Studio. Thời gian chạy tỉ lệ thuận với kích thước tài liệu trên mô hình cục bộ — vài phút cho một README nhỏ, và có thể lên đến một giờ cho một tài liệu lớn được chia nhỏ.

Những ngôn ngữ đã có tệp `docs/<language>/README.md` sẽ không bị dịch lại từ đầu: người hiệu đính sẽ so sánh bản dịch hiện có với bản nguồn hiện tại và chỉ khi có thay đổi, người viết mới vá lỗi bằng những chỉnh sửa tối thiểu. Các bản dịch đã cập nhật sẽ được bỏ qua hoàn toàn, vì vậy việc chạy lại pipeline sau khi chỉnh sửa README chỉ thực hiện lại những phần đã cũ.

Sau khi hoàn tất công việc cho từng ngôn ngữ, quá trình chạy kết thúc bằng cách (nếu cần) di chuyển tệp `README.md` nguồn ở gốc vào `docs/<source_language>/` và tạo lại tệp `README.md` ở gốc thành một trang chọn ngôn ngữ ngắn gọn liên kết đến mọi bản dịch không trống.

Yêu cầu server cục bộ của LM Studio đang chạy (xem `config.json`) với bất kỳ mô hình chat nào được tải — pipeline điều khiển mô hình bằng các completion văn bản thuần túy và tự thực hiện ghi tệp, vì vậy mô hình **không** cần hỗ trợ tool calls kiểu OpenAI (xem "Xử lý README lớn" bên dưới). Tuy nhiên, bạn nên thử nghiệm với một ngôn ngữ trước khi chạy toàn bộ danh sách.

### Xử lý README lớn

Việc dịch một README lớn (ví dụ hai tài liệu `A-Starry-Sky` / `a-restless-ocean` khoảng 35–60 KB) trong một lần completion duy nhất là rủi ro chính về độ tin cậy trên mô hình cục bộ: nó có thể hết token đầu ra hoặc tràn ngữ cảnh giữa chừng và phần cuối bị cắt cụt một cách âm thầm. Chế độ `pipeline` được xây dựng để tránh điều này:

- **Thiết kế không dùng tool.** Mô hình chỉ tạo ra văn bản thuần túy — mọi bản dịch, bản viết lại và trang thư mục đều trả về dưới dạng câu trả lời, và bộ điều phối (orchestrator) sẽ tự lưu chúng thông qua các công cụ `write_readme` / `write_directory_readme` của server. Không có yêu cầu nào bắt mô hình phải nhồi nhét toàn bộ tài liệu vào một đối số của tool-call. Trên các mô hình *suy luận* cục bộ (ví dụ: Gemma 4), cách làm đó sẽ khiến JSON của đối số bị cắt cụt và endpoint sẽ từ chối với lỗi `peg-gemma4 format` / malformed-output; việc trả về văn bản thuần túy giúp tránh hoàn toàn vấn đề này.
- **`max_tokens`** (mặc định `32768`) được gửi rõ ràng trong mỗi lần completion để một phần/bản nháp đầy đủ có thể hoàn thành thay vì bị cắt bởi mặc định nhỏ hơn của LM Studio cho mỗi yêu cầu. Pipeline sẽ cảnh báo nếu một completion vẫn dừng do `length`, để bạn biết mà tăng giá trị này lên.
- **Chia nhỏ theo phần (Section chunking)** — khi nguồn vượt quá `chunk_threshold_chars` (mặc định `12000`) và `chunk_translation` là `true`, nguồn sẽ được chia theo các tiêu đề Markdown cấp cao nhất (`## `) (có nhận diện khối code, nên `##` bên trong code block sẽ được giữ nguyên), mỗi phần được dịch trong một lần completion riêng, sau đó bộ điều phối sẽ lắp ghép các mảnh lại và lưu. Không có cuộc gọi mô hình đơn lẻ nào phải xuất ra toàn bộ tài liệu.
- **Hiệu đính theo từng phần** — với `review_sections` là `true` (mặc định), mỗi phần sẽ chạy cùng một vòng lặp phê bình $\rightarrow$ chỉnh sửa như quy trình một lần, nhưng chỉ giới hạn trong phần đó: người hiệu đính so sánh phần đã dịch với nguồn và người viết chỉnh sửa cho đến khi người hiệu đính đồng ý (hoặc đạt `MAX_ITERATIONS`). Vì mỗi phần đều nhỏ, việc hiệu đính và viết lại sẽ nằm an toàn dưới ngưỡng bị cắt cụt, điều mà việc hiệu đính toàn bộ một README lớn không làm được.

Quy trình chia nhỏ cố tình **không** chạy lượt hiệu đính toàn bộ tài liệu lần thứ hai sau đó — vì việc xuất lại toàn bộ README lớn trong một lần completion sẽ tái diễn lỗi cắt cụt, và lượt kiểm tra theo từng phần đã bao quát hết nội dung. Hãy đặt `review_sections` thành `false` để dịch các tài liệu lớn mà không cần hiệu đính, hoặc `chunk_translation` thành `false` để ép buộc hành vi chạy một lần ban đầu (vẫn chạy vòng lặp hiệu đính toàn bộ tài liệu). Quy trình chạy một lần cho các tệp dưới ngưỡng chia nhỏ vẫn giữ nguyên.