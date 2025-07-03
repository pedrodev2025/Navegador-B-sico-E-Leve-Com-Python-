# Navegador-B-sico-E-Leve-Com-Python-
# Como Usar 
Para usar Primeiro Baixe As dependências 
```bash
sudo pacman -S python3 --noconfirm
sudo pacman -S python-pip --noconfirm # Substitua pacman pelo seu gerenciador de pacotes e suas flags # a maioria das distros vem com o venv ja no pacote python mas algumas(especialmente debian/ubuntu) precisa instalar separadamente
python3 -m venv ~/.venv
source ~/.venv/bin/activate # se usa bash
# source ~/.venv/bin/activate.fish # se usa fish
# source ~/.venv/bin/activate.ps1 # se usa powershell
pip install PyQt5 cefpython3
```
depois baixe o navegador
```bash
sudo pacman -S git
git clone https://github.com/pedrodev2025/Navegador-B-sico-E-Leve-Com-Python-.git
```
depois Entre no Repositório
```bash
cd Navegador-B-sico-E-Leve-Com-Python-
```
depois execute 
```bash
python3 navegador.py
```
