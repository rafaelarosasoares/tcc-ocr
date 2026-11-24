# Autenticação

Habilite a **Google Drive API** no projeto Google Cloud das credenciais.
O acesso ao Drive usa somente o escopo `drive.readonly`; os arquivos da
origem não são modificados.

Se já usa uma conta de serviço no OCR, compartilhe a pasta do Drive como
**Leitor** com o e-mail dessa conta e use seu arquivo de credenciais:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/fora/do/repositorio/service-account.json"
```

A conta também precisa das permissões existentes para Document AI e Vertex AI
para executar o processamento completo.

Para autenticar com sua conta pessoal, configure a tela de consentimento OAuth
(adicione seu e-mail como usuário de teste, se o app estiver em teste), crie um
cliente OAuth do tipo **Aplicativo para computador** e baixe o JSON. Em seguida,
gere as credenciais padrão com os escopos do Drive e do OCR:

```sh
gcloud auth application-default login \
  --client-id-file="/caminho/client_secret.json" \
  --scopes="https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/cloud-platform"
```

Nesse modo, `GOOGLE_APPLICATION_CREDENTIALS` deve estar desdefinida para que
as credenciais geradas pelo `gcloud` sejam usadas. Não coloque credenciais no Git.
Detalhes na documentação de [credenciais padrão](https://cloud.google.com/docs/authentication/application-default-credentials)
e de [login com escopos adicionais](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login).

Se aparecer `Request had insufficient authentication scopes`, as credenciais
locais não foram autorizadas para o Drive. Refaça o login acima com o cliente
OAuth e os dois escopos, ou use uma conta de serviço com acesso à pasta.
O login do conector Google Drive no Codex é independente das credenciais do
script Python.

