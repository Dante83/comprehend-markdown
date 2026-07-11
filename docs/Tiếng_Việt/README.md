# comprehend-markdown

*Bạn chạm tay vào cuộn giấy và đọc lời chú. Vài phút hoặc một giờ sau (tùy theo độ dày của cuộn giấy), bạn sẽ thấu hiểu mọi nội dung Markdown bằng bất kỳ ngôn ngữ nào.*

Đây là một máy chủ MCP giúp dịch tệp `README.md` của dự án sang các ngôn ngữ khác, đi kèm với một pipeline độc lập chạy vòng lặp viết/kiểm duyệt (writer/reviewer loop) sử dụng mô hình LM Studio cục bộ.

Ngôn ngữ nguồn và ngôn ngữ đích đều có thể cấu hình được — tiếng Anh chỉ là mặc định. Hãy thiết lập `source_language` để dịch *từ* tiếng Trung, tiếng Indonesia hoặc bất kỳ ngôn ngữ nào khác, và `target_languages` để chọn các ngôn ngữ cần chuyển đổi sang (xem mục [Chọn ngôn ngữ nguồn và đích](#chọn-ngôn-ngữ-nguồn-và-đích)).

Đối với bất kỳ dự án mục tiêu nào, công cụ này yêu cầu (và sẽ tự động tạo nếu cần):

```
<project-root>/docs/<source>/README.md  bản nguồn chuẩn (mặc định là tiếng Anh)
<project-root>/docs/<lang>/README.md    các bản dịch, mỗi ngôn ngữ một tệp
<project-root>/README.md                trang điều hướng chọn ngôn ngữ (tự động tạo)
```

Với những dự án chưa được di chuyển — khi bản nguồn vẫn nằm ở thư mục gốc — công cụ vẫn hoạt động bình thường: tệp `README.md` ở gốc sẽ được dùng làm nguồn, và sau khi kết thúc chạy `pipeline`, nó sẽ được chuyển vào `docs/<source>/` (ví dụ: `docs/English/`) và được thay thế bằng một trang điều hướng ngắn gọn chứa liên kết đến tất cả các bản dịch hiện có.

## Cài đặt

Mọi thứ (tạo venv, cài đặt/đồng bộ hóa gói phụ thuộc) đều được xử lý bởi `run.sh` — không cần bước cài đặt riêng biệt. Script này đọc các gói từ `requirements.txt` và cài đặt lại mỗi khi chạy, vì vậy để cập nhật các phụ thuộc mới, bạn chỉ cần chạy lại script.

Nếu bạn muốn sử dụng một mô hình LM Studio cục bộ khác với mặc định, hãy sửa các giá trị trong `config.json`.

### Chọn ngôn ngữ nguồn và đích

Hai khóa cấu hình trong `config.json` điều khiển hướng dịch:

- **`source_language`** — ngôn ngữ mà tệp `README.md` chuẩn được viết, đồng thời là tên của thư mục `docs/<source_language>/`. Mặc định là `English`. Bạn có thể đặt thành `中文`, `Indonesia`, hoặc bất kỳ ngôn ngữ nào khác để dịch *từ* ngôn ngữ đó.
- **`target_languages`** — danh sách các ngôn ngữ mà pipeline sẽ dịch *sang*. Bất kỳ mục nào trùng với `source_language` sẽ tự động được bỏ qua, nên việc để ngôn ngữ nguồn trong danh sách này là không gây hại gì.

Ví dụ, để dịch một tệp README tiếng Trung sang tiếng Anh và tiếng Tây Ban Nha:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Nếu `target_languages` bị bỏ trống, pipeline sẽ quay về sử dụng danh sách 18 ngôn ngữ tích hợp sẵn.

`api_key` chỉ có tác dụng nếu bạn bật "Require API Key" trong cài đặt Developer server của LM Studio — nếu không, hãy để mặc định là `"lm-studio"`, giá trị này sẽ được LM Studio bỏ qua. Lưu ý rằng điều này chỉ áp dụng cho chế độ `pipeline`, vì đây là phần duy nhất gọi trực tiếp đến endpoint tương thích OpenAI của LM Studio; chế độ `serve` không bao giờ giao tiếp với API của LM Studio vì chính LM Studio đóng vai trò là MCP client gọi vào máy chủ này.

Bạn có thể thiết lập `max_tokens` tại đây, nhưng tôi không chắc liệu LM Studio có thực sự tuân thủ giá trị này hay không. Hãy đảm bảo bạn đã đặt giá trị này ít nhất khoảng 24576 trong chính mô hình trước khi chạy script.

## Sử dụng

```bash
./run.sh serve    /absolute/path/to/project   # máy chủ MCP stdio
./run.sh pipeline /absolute/path/to/project   # chạy main.py từ đầu đến cuối
```

Cả hai chế độ đều yêu cầu đường dẫn **tuyệt đối** đến thư mục dự án chứa tệp `README.md` cần dịch. Trong chế độ `pipeline`, bạn có thể bỏ qua đường dẫn này và nhập sau khi được nhắc, miễn là bạn đang chạy tương tác trong terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(Chế độ `serve` không bao giờ yêu cầu nhập liệu — một khi khởi động, stdin/stdout sẽ trở thành kênh JSON-RPC của MCP, và các host MCP thường khởi chạy nó ở chế độ không tương tác.)

### `serve` — sử dụng như một công cụ cho MCP host

Đây là lệnh mà một MCP host (ví dụ: LM Studio) nên trỏ đến trong phần cấu hình `command` của server, với đường dẫn tuyệt đối của dự án mục tiêu làm đối số cố định. Nó cung cấp:

- **tool** `write_readme(language, content)` — ghi tệp `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — ghi tệp `README.md` ở gốc (trang điều hướng chọn ngôn ngữ)
- **resource** `docs://readme` — bản nguồn (`docs/<source_language>/README.md`, hoặc mặc định là `README.md` ở gốc)
- **resource** `docs://readme/{language}` — bản dịch hiện có, nếu có
- **resource** `docs://dir_readme` — tệp `README.md` ở gốc
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — vòng lặp dịch mới
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — quy trình cập nhật: so sánh bản dịch hiện có với bản nguồn hiện tại và vá lỗi với những thay đổi tối thiểu
- **prompt** `create_docs_language_directory` — xây dựng trang điều hướng chọn ngôn ngữ ở gốc từ danh sách các bản dịch hiện có

Mô hình của chính host sẽ điều khiển việc gọi công cụ; máy chủ này chỉ cung cấp khả năng đọc/ghi tệp và các mẫu prompt.

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

Đối số `args` thứ hai được cố định tại thời điểm kết nối — cấu hình của LM Studio là JSON tĩnh và không hỗ trợ nhập liệu tương tác, vì vậy đó phải là đường dẫn thực tế mà bạn muốn dịch, chứ không phải đường dẫn của repo này (trừ khi chính repo này là dự án bạn muốn dịch).