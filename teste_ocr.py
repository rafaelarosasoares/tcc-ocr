import json

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.protobuf.json_format import MessageToDict

PROJECT_ID = "project-5e3bf1fd-47b5-442e-90d"
LOCATION = "us"
PROCESSOR_ID = "15f792d10b41ff08"

FILE_PATH = "folha.jpg"
MIME_TYPE = "image/jpeg"

opts = ClientOptions(
    api_endpoint=f"{LOCATION}-documentai.googleapis.com"
)

client = documentai.DocumentProcessorServiceClient(
    client_options=opts
)

name = client.processor_path(
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID
)

with open(FILE_PATH, "rb") as file:
    file_content = file.read()

raw_document = documentai.RawDocument(
    content=file_content,
    mime_type=MIME_TYPE
)

request = documentai.ProcessRequest(
    name=name,
    raw_document=raw_document
)

result = client.process_document(request=request)

document = result.document

print("\n===== TEXTO EXTRAÍDO =====\n")
print(document.text)

document_dict = MessageToDict(
    document._pb,
    preserving_proto_field_name=True
)

with open("resultado_document_ai.json", "w", encoding="utf-8") as arquivo:
    json.dump(
        document_dict,
        arquivo,
        ensure_ascii=False,
        indent=2
    )

print("\nJSON salvo em resultado_document_ai.json")