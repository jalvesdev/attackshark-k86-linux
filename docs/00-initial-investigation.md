# Relatório inicial — ATTACK SHARK K86

Data: 2026-10-21. Escopo executado: identificação do hardware disponível, inventário/extração estática do instalador, verificação do REA, busca de projetos existentes e análise preliminar dos binários. Nenhum executável Windows foi iniciado; nenhum comando USB de escrita foi enviado; firmware e configurações do sistema não foram alterados.

## Resumo das evidências

- O instalador original foi preservado; SHA-256 `3ee70880c8b5adcd469a0e3ebefa7e280a22fa23ff74e369955511a2c58e04a2`.
- O arquivo é instalador NSIS 3 Unicode. O 7-Zip listou o arquivo interno `app-32.7z`; ele foi extraído em `/tmp` e listado sem executar seus conteúdos.
- A aplicação é Electron/React; contém um helper nativo `iot_driver.exe`. Os imports do helper incluem `DeviceIoControl`, `CreateFileW`, `ReadFile`, `WriteFile` e variantes NT de I/O. Strings do binário indicam compilação Rust e incluem uma tabela de dispositivos HID, incluindo `3151:4011`, `3151:4015`, `3151:4012`, `3151:5002` e `3151:5056`.
- O REA MCP respondeu e abriu o PE principal e o helper. Ghidra 12.1.4 é o provedor anunciado para análise profunda. A visão geral e busca de strings no helper excederam 300 s; o parser PE de recursos do REA conseguiu enumerar 11 entradas. Não há análise dinâmica nem pseudocódigo útil do helper ainda.
- Após a conexão por cabo, o teclado foi detectado em `/sys/bus/usb/devices/1-1.2`, VID:PID `3151:4015`, revisão `01.14`, fabricante ROYUAN, produto `Gaming Keyboard`, com três interfaces HID. O ID coincide com uma variante com fio do K86 listada pelo projeto comunitário `sharkfin`; isso reforça a identificação, embora o firmware não tenha sido consultado.
- O receptor `3151:4011` continua conectado em `/sys/bus/usb/devices/1-1.4`. Assim, ambos aparecem simultaneamente e são distinguíveis por VID:PID e caminho físico.
- `lsusb` retorna erro libusb `-99`. O udev aponta `hidraw9` para o dispositivo, mas `/dev/hidraw9` não está visível neste ambiente. Os report descriptors das três interfaces com fio foram lidos somente pelo sysfs: keyboard boot, controles/teclas multimídia com coleção vendor-defined (Report ID 5, 3 bytes de entrada), e uma interface vendor-defined com Feature Report ID implícito 0 e 64 bytes. Nenhum pacote HID foi enviado ou lido do teclado.
- Pesquisa encontrou o `sharkfin`, que lista três revisões K86 graváveis: `3151:4015` (yc500), `3151:5002` (gen2) e `3151:5056` (gen2). A documentação alerta que revisões usam controladoras e famílias de protocolo diferentes. É referência comunitária, não validação da unidade local.

## Matriz preliminar de capacidades

| Capacidade | Evidência atual | Estado para este projeto |
|---|---|---|
| USB com fio | Dispositivo local `3151:4015` em três interfaces; PID listado para variante K86 yc500 no catálogo comunitário | Identificado como candidato K86 com fio; revisão interna ainda não verificada |
| Receptor 2,4 GHz | Receptor local `3151:4011`; helper inclui interface HID vendor; comunidade relata relay variável entre dongles | Dependente da unidade; somente identificação/leitura segura após provar comportamento |
| Bluetooth | Comunidade diz que o K86 não expõe canal de configurações; detector OpenRGB de fork permanece comentado | Sem suporte de configuração confirmado |
| RGB: efeitos, cor, brilho, velocidade | Catálogo comunitário K86 lista 18 efeitos e controles RGB | Implementável em princípio; não testado aqui e provavelmente varia por revisão |
| Cor por tecla | Catálogo `sharkfin` lista paint/per-key color | Implementável em princípio; sem validação local |
| Remapeamento e camada Fn | Catálogo lista as camadas base/Fn | Implementável em princípio; sem validação local |
| Macros | Catálogo lista até 50 slots onboard | Implementável em princípio; sem validação local |
| Perfis | Catálogo indica três perfis embarcados nas revisões K86 | Implementável em princípio; sem validação local |
| Knob, borda RGB, tela | Listados somente para revisões específicas no catálogo K86 | Depende da revisão; não presumir na unidade física |
| Relatórios HID | Documento comunitário afirma Feature Reports de 64 bytes e famílias `yc500`/`gen2` com semântica diferente | Referência de análise; não reproduzida nem enviada ao dispositivo |
| Firmware | Existe documentação de bootloader de terceiros; não é necessária para configurar | Fora do escopo; nenhum acesso/alteração |

## Riscos e bloqueios

1. **Revisão interna:** `3151:4015` aponta para uma variante com fio K86 yc500 na referência comunitária, mas não consultamos um ID interno do teclado.
2. **Acesso hidraw:** os descriptors estão disponíveis pelo sysfs, mas o nó `/dev/hidraw9` anunciado por udev não está visível no ambiente; ainda não há acesso a operações hidraw.
3. **Análise REA do helper:** Ghidra excedeu 300 segundos em duas consultas; obter rotinas de comunicação continua bloqueado. A análise estática local de imports e strings é preliminar e não descreve fluxo de dados.
4. **Protocolos incompatíveis:** fontes comunitárias indicam mais de uma família; usar a família errada pode gravar dados em campos de significado diferente. Não enviar comandos de escrita.
5. **Persistência:** configurações podem ficar armazenadas no teclado. Testes de escrita futuros precisam autorização explícita e plano de restauração.
6. **Compatibilidade upstream:** não foi confirmada integração do K86 no OpenRGB upstream; há código num fork comunitário. OpenRazer é voltado a Razer; libratbag tem conversa sobre um mouse Attack Shark, não o teclado K86.

## Próximos passos

1. Confirmar o modo do seletor físico usado e disponibilizar o nó hidraw da interface vendor-defined para análise somente de leitura, se necessário.
2. Repetir análise REA focada por provedores/consultas menores ou Ghidra em ambiente configurado, começando pelo mapa de strings/procedures/imports do helper. Não executar o helper.
3. Rastrear como o bundle Electron se comunica com `iot_driver.exe` e quais funções do software original existem.
4. Comparar evidências próprias com a documentação pública do protocolo, identificando claramente o que é código do fornecedor, firmware e teste comunitário.
5. Só depois escolher consultas de leitura para um CLI em simulação primeiro; nenhuma escrita até protocolo e risco validados.

## Arquivos de evidência

- [Ambiente e USB](00-environment-report.md)
- [Inventário de binários](01-binary-inventory.md)
- [Arquitetura observada](01-software-architecture.md)
- [Compatibilidade comunitária](01-community-compatibility.md)

## Aditivo do ciclo 2

A enumeração via sysfs/kernel e os descritores das três interfaces HID do teclado com fio permanecem registrados em `00-environment-report.md`; a ausência de `/dev/hidraw*` no ambiente impediu obter o device ID interno. A ficha atual do sharkfin confirma a associação de catálogo `3151:4015` → K86 device ID 1168, controlador yc3121 e protocolo yc500. Assim, a revisão local é provável, mas não confirmada internamente. O receptor `3151:4011` continua separado e sua associação não foi usada para identificar a revisão. Consulte os relatórios `02-device-identification.md`, `02-community-protocol-analysis.md`, `02-grpc-api.md`, `02-helper-analysis.md` e `02-protocol-comparison.md` para os resultados do ciclo.

Os arquivos extraídos permanecem em `/tmp/attack-shark-inventory` e `/tmp/attack-shark-app-32.7z`. Binários proprietários não foram copiados para o projeto.
