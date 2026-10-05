# DevicePulse

Bateria de mouse, teclado e fone na barra do Omarchy. Um ícone, um painel compacto, sem precisar abrir o driver do fabricante.

## O que aparece

- Percentual e estado de carga por dispositivo.
- Bluetooth pareado, inclusive quando está desconectado. A última leitura fica identificada como histórica.
- Histórico das últimas 24 horas. O gráfico aparece quando a carga muda; os dados ficam guardados por 30 dias.
- Avisos em 20% e 10%, sem repetir a cada atualização.
- Receptor USB presente e bateria não informada aparecem como estados distintos. Sem percentual disponível, o painel não inventa 0%.

O ícone destaca bateria baixa. Clique pra abrir; botão do meio pra atualizar. Esc fecha o painel, e as setas rolam a lista quando ela não cabe na tela.

## Instalar

Requer Omarchy com a barra Quickshell e o sistema de plugins, Python 3, `python-dbus`, UPower e systemd do usuário. A versão antiga com Waybar não é compatível.

```bash
git clone https://github.com/LucasOl1337/omarchy-device-pulse.git
cd omarchy-device-pulse
python3 install.py
```

Pra ler os mouses MCHOSE com receptor `5253:1020`, instale também a regra de acesso USB:

```bash
python3 install.py --udev
```

Essa opção usa sudo pra instalar uma regra udev restrita ao receptor. O coletor roda como usuário comum. Rodar o instalador de novo atualiza os arquivos sem apagar o histórico ou mudar a posição do ícone.

## Dispositivos

| Fonte | Cobertura |
| --- | --- |
| UPower | Periféricos com bateria exposta pelo Linux, como Logitech HID++ |
| BlueZ | Dispositivos pareados, com percentual quando `org.bluez.Battery1` está disponível e o aparelho está conectado |
| MCHOSE USB | Leitura de identidade do mouse no receptor `5253:1020`; testado no K7 Ultra |
| AJAZZ `3151:5007` e MCHOSE X9 `3837:6045` | Receptor detectado; percentual ainda não suportado |

Um dongle conectado não prova que o aparelho está ligado. Por isso o painel informa "Receptor detectado" quando não consegue ler a telemetria. Nomes de outros receptores podem precisar de suporte específico.

A leitura MCHOSE segue a documentação de [alexfrih/mchose-linux](https://github.com/alexfrih/mchose-linux/blob/main/PROTOCOL.md): somente a consulta de identidade `0x11/0x06`, sem comandos de configuração, DPI ou firmware.

## Manutenção

```bash
systemctl --user status omarchy-device-pulse.timer
systemctl --user start omarchy-device-pulse.service
python3 collect.py --json
python3 -m unittest discover -s tests -v
python3 install.py --uninstall
```

A coleta roda a cada minuto e publica um JSON pro painel. O histórico fica em `~/.local/state/omarchy-device-pulse/history.sqlite`. A remoção preserva esses dados e a regra USB opcional; pra remover a regra também, apague `/etc/udev/rules.d/70-device-pulse-mchose.rules` e recarregue o udev.

## Contribuir

Abra uma issue com o modelo, o ID USB de `lsusb`, a fonte de bateria que o Linux expõe e o resultado esperado. Não inclua serial, endereço Bluetooth ou credenciais. Pra adicionar um protocolo, documente a consulta, valide as respostas e mantenha alterações de configuração fora do coletor.

Licença MIT.
