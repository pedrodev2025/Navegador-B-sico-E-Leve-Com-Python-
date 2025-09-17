# Navegador Simples e Leve com Python

Este é um navegador web básico e leve desenvolvido em Python, utilizando a biblioteca **PyQt5** e o **QtWebEngine** (que é baseado no Chromium). Ele foi projetado para ser fácil de usar e inclui funcionalidades essenciais como navegação, gerenciamento de perfis e busca inteligente.

## Funcionalidades Principais

* **Navegação Essencial:** Botões de Voltar, Avançar, Recarregar e Home.
* **Barra de URL Inteligente:** Detecta automaticamente se o que foi digitado é uma URL ou um termo de pesquisa, usando o Google como padrão. Inclui um ícone de cadeado para indicar a segurança da conexão (HTTPS).
* **Gerenciamento de Perfis:**
    * Inicie no **Modo Convidado** (sem salvar histórico ou cookies).
    * Crie e carregue **perfis persistentes** para manter seus dados de navegação.
    * Opção para **deletar** perfis existentes.
* **Leve e Flexível:** Desenvolvido em Python para fácil customização e entendimento.

## Como Usar

Para colocar o navegador para funcionar, siga os passos abaixo:

### 1. Pré-requisitos e Instalação de Dependências

Este projeto foi desenvolvido e testado no **Arch Linux**, e as instruções de instalação das dependências refletem isso.

É **altamente recomendado** usar um ambiente virtual para isolar as dependências do projeto do restante do seu sistema Python.

#### No Arch Linux:

1.  **Instale Python e `pip` (se ainda não tiver):**
    ```bash
    sudo pacman -S python python-pip
    ```
2.  **Crie e Ative o Ambiente Virtual:**
    ```bash
    python3 -m venv ~/.venv/navegador-env
    source ~/.venv/navegador-env/bin/activate
    ```
    * **Para usuários Fish Shell:** Use `source ~/.venv/navegador-env/bin/activate.fish`
    * **Para usuários PowerShell:** Use `~/.venv/navegador-env/Scripts/Activate.ps1`
    *(Se você usa Debian/Ubuntu, talvez precise instalar `python3-venv` separadamente com `sudo apt install python3-venv`.)*

3.  **Instale as Bibliotecas PyQt5 e PyQtWebEngine:**
    ```bash
    pip install PyQt5 PyQtWebEngine
    ```
    * **Observação para Arch Linux:** Para o `PyQtWebEngine` funcionar corretamente com o Qt5, é fundamental que as bibliotecas base do Qt5 WebEngine estejam instaladas no sistema. Se você tiver problemas, tente instalar os pacotes do sistema:
        ```bash
        sudo pacman -S python-pyqt5 python-pyqt5-webengine
        ```
        Se você já instalou `python-pyqt6` anteriormente, não se preocupe, `pacman` deve gerenciar as dependências do `python-pyqt5-webengine` corretamente.

### 2. Baixe o Navegador

Se você ainda não clonou o repositório, faça isso:

```bash
sudo pacman -S git # Instala o Git, se ainda não estiver instalado
git clone https://github.com/pedrodev2025/Navegador-B-sico-E-Leve-Com-Python-.git
