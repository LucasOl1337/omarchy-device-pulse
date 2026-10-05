# DevicePulse v1.1.1

5 de outubro de 2026

Bateria e configurações dos periféricos na barra.

## Novidades

- **Bateria dos seus dispositivos.** Mouse, teclado e fone juntos, com leitura do Linux e receptores suportados.
- **DPI e polling rate pelo painel.** Escolha etapas ou DPI personalizado e ajuste a frequência do K7 Ultra.
- **Histórico e avisos de carga.** Veja as últimas 24 horas e receba avisos em 20% e 10%.

## Melhorias

- **Painel mais compacto.** Os controles ficam no cartão do mouse e abrem quando você precisa.

## Correções

- **Bateria do MCHOSE X9.** O receptor 2.4 GHz agora informa o percentual do fone ligado.
- **Atualização que aparece na barra.** O instalador evita o cache que mantinha a interface antiga.

## Instalar ou atualizar

```bash
git clone https://github.com/LucasOl1337/omarchy-device-pulse.git
cd omarchy-device-pulse
python3 install.py --udev
```

Se você já tem o clone, rode `git pull` antes do instalador. A regra USB pede sudo. O histórico e a posição do ícone continuam onde estão.

Edição de DPI e polling rate validada no MCHOSE K7 Ultra. O X9 tem leitura de bateria. O receptor AJAZZ é detectado, mas ainda não informa bateria nem oferece edição. Requer Omarchy com Quickshell e plugins.

## Verificado

20 testes Python passaram. Plugin validado e versão carregada na barra conferida por diagnóstico IPC.
