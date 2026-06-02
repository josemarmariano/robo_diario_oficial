O sistema é um robô em Python para monitorar automaticamente o Diário Oficial de Piracicaba/SP, baixando a edição do dia, extraindo o conteúdo pesquisável, estruturando as informações em JSON, procurando termos de interesse e enviando alerta por e-mail quando houver ocorrência relevante.

As principais entregas atuais são: PDF baixado, TXT bruto para auditoria, JSON estruturado para pesquisa, JSON com resultado da pesquisa e envio de e-mail de alerta. O TXT bruto funciona como prova da extração original; o JSON estruturado é a base operacional para busca; o JSON de pesquisa registra quais termos foram encontrados, em qual arquivo, seção, página e quantidade de ocorrências.

A rastreabilidade segue esta cadeia:

PDF original
↓
01_bruto.txt
↓
02_documento.json
↓
resultado_pesquisa_<data>.json
↓
e-mail de alerta

O fluxo de funcionamento é:

1. Ler configurações do .env
2. Montar a URL do Diário Oficial pela data
3. Baixar o PDF
4. Extrair texto página por página
5. Gerar TXT bruto
6. Identificar sumário e seções
7. Gerar JSON estruturado
8. Varrer os JSONs da pasta de resultados
9. Pesquisar termos configurados
10. Gerar JSON de resultado da pesquisa
11. Montar e enviar e-mail de alerta
12. Registrar tudo em log

A regra central do projeto é: o robô não tenta “entender visualmente” o PDF inteiro; ele foca em capturar conteúdo textual relevante para monitoramento, como leis, decretos, licitações, ISS, IPASP, SAAE, isenções, comunicados e outros assuntos definidos pelo usuário.



