# DevicePulse

Bateria e configurações dos seus periféricos na barra do Omarchy. Um ícone, um painel compacto, com controles de DPI e polling rate nos modelos suportados.

## O que aparece

- Percentual e estado de carga por dispositivo.
- DPI atual e polling rate do MCHOSE K7 Ultra, com etapas, valor personalizado e troca de frequência pelo painel.
- RGB do Logitech G515 LS TKL: cor fixa no teclado inteiro, com botão Laranja e opção de apagar.
- Bluetooth pareado, inclusive quando está desconectado. A última leitura fica identificada como histórica.
- Histórico das últimas 24 horas. O gráfico aparece quando a carga muda; os dados ficam guardados por 30 dias.
- Avisos em 20% e 10%, sem repetir a cada atualização.
- Receptor USB presente e bateria não informada aparecem como estados distintos. Sem percentual disponível, o painel não inventa 0%.

O ícone de dispositivos representa os periféricos e fica destacado quando alguma bateria está baixa. Clique pra abrir; botão do meio pra atualizar. Esc fecha o painel, e as setas rolam a lista quando ela não cabe na tela.

## Instalar

Requer Omarchy com a barra Quickshell e o sistema de plugins, Python 3, `python-dbus`, UPower e systemd do usuário. A versão antiga com Waybar não é compatível.

```bash
git clone https://github.com/LucasOl1337/omarchy-device-pulse.git
cd omarchy-device-pulse
python3 install.py
```

Pra ler e configurar o K7 Ultra com receptor `5253:1020`, ler a bateria do X9 `3837:6045`, ou do AJAZZ `3151:5007`, instale também as regras de acesso USB:

```bash
python3 install.py --udev
```

Essa opção usa sudo pra instalar regras udev restritas aos receptores suportados. O coletor roda como usuário comum. Rodar o instalador de novo atualiza os arquivos sem apagar o histórico ou mudar a posição do ícone.

Cada atualização publica o QML em `.runtime/<hash>/`, evitando que a barra continue usando a interface antiga em cache. Pra conferir a versão carregada: `quickshell ipc -p /usr/share/omarchy/shell call lucasol.device-pulse diagnostics`.

## Dispositivos

| Fonte | Cobertura |
| --- | --- |
| UPower | Periféricos com bateria exposta pelo Linux, como Logitech HID++ |
| BlueZ | Dispositivos pareados, com percentual quando `org.bluez.Battery1` está disponível e o aparelho está conectado |
| MCHOSE K7 Ultra `5253:1020` | Bateria, DPI atual, etapas e polling rate; edição validada neste modelo |
| MCHOSE X9 `3837:6045` | Bateria pelo receptor 2.4 GHz; validado em hardware real |
| AJAZZ 2.4G 8K `3151:5007` | Bateria pelo receptor, validada em hardware real; edição de configurações ainda sem suporte |

Um dongle conectado não prova que o aparelho está ligado. Por isso o painel informa "Receptor detectado" quando não consegue ler a telemetria. Nomes de outros receptores podem precisar de suporte específico.

O protocolo do mouse segue a documentação de [alexfrih/mchose-linux](https://github.com/alexfrih/mchose-linux/blob/main/PROTOCOL.md). A bateria do X9 usa o protocolo de status documentado pelo [HeadsetControl](https://github.com/Sapd/HeadsetControl/blob/master/lib/devices/mchose_x9.hpp): consulta `55 65 01`, resposta com campo de bateria `02`. O coletor valida dispositivo, interface, assinatura e percentual.

## Ajustar o mouse

No K7 Ultra, clique em **Ajustar**. Você pode escolher uma etapa de DPI, editar o valor da etapa atual em passos de 50 ou trocar o polling rate. A edição de DPI coloca X e Y no mesmo valor. A seleção de etapa e polling rate vale pro link do receptor; a configuração do link por cabo fica preservada.

O coletor só lê. O controlador escreve apenas depois da sua ação no painel, guarda a configuração anterior e confere a leitura de volta. Só mostra sucesso quando o mouse confirma a mudança. Backups ficam em `~/.local/state/omarchy-device-pulse/mouse-before-*.json`; não vão pro repo.

Quando o mouse dorme ou sai de alcance, o painel guarda a última configuração como anterior e desabilita a edição. Movimente o mouse e reabra o painel pra buscar a leitura atual. A edição de outros modelos ainda depende de validação do protocolo.

A bateria do AJAZZ usa a consulta de status `F7` e o relatório HID de bateria documentados no [AJAZZ Control Center](https://github.com/Aiacos/ajazz-control-center/blob/develop/docs/protocols/mouse/aj_series_battery.md). A consulta não altera DPI, botões ou perfil. Respostas vazias, incompletas ou fora de 1–100% ficam como desconhecidas.

## RGB do teclado

No cartão do **Logitech G515 LS TKL**, abra **Ajustar** e escolha **Laranja**, outra cor ou **Apagar**. Laranja usa RGB 200, 50, 0 (`C83200`). O campo HEX aceita qualquer cor de seis dígitos. Requer `openrgb` com suporte ao G515 (validado com 1.0rc3) e configuração de detectores gerada pela primeira execução do OpenRGB. O teclado precisa estar acordado e conectado.

O controle usa uma configuração separada que habilita somente os detectores do G515, evitando consultar RAM, GPU e placa-mãe. A coleta de bateria não chama OpenRGB. A cor selecionada fica salva localmente. O serviço `omarchy-device-pulse-rgb.service` mantém o controlador OpenRGB ativo, em modo host, e inicia novamente no login. O servidor RGB escuta somente em `127.0.0.1:16743` e detecta apenas o G515. Não há escrita de perfil na memória flash do teclado. A cor mostrada é a seleção enviada, não uma leitura da iluminação física. O retorno após suspensão/reconexão ainda depende de validação física.

Também aceita qualquer cor pela linha de comando, usando o ID do teclado publicado no `status.json`:

```bash
python3 control.py --device 'ID_DO_TECLADO' --color C83200
```

## Manutenção

```bash
systemctl --user status omarchy-device-pulse.timer omarchy-device-pulse-rgb.service
systemctl --user start omarchy-device-pulse.service
python3 collect.py --json
python3 -m unittest discover -s tests -v
python3 install.py --uninstall
```

A coleta roda a cada minuto e publica um JSON pro painel. O histórico fica em `~/.local/state/omarchy-device-pulse/history.sqlite`. A remoção preserva esses dados e a regra USB opcional; pra remover a regra também, apague `/etc/udev/rules.d/70-device-pulse-mchose.rules` e recarregue o udev.

## Contribuir

Abra uma issue com o modelo, o ID USB de `lsusb`, a fonte de bateria que o Linux expõe e o resultado esperado. Não inclua serial, endereço Bluetooth ou credenciais. Pra adicionar um protocolo, documente a consulta, valide as respostas e mantenha alterações de configuração fora do coletor.

Licença MIT.
