import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *

class BrowserTab(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load(QUrl("https://www.google.com")) # Página inicial padrão para cada nova guia

class MiniNavegador(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Navegador Py-Tech") # Novo título
        self.resize(1200, 800) # Aumenta o tamanho da janela

        # Barra de navegação (Toolbar)
        self.toolbar = QToolBar("Navegação")
        self.addToolBar(self.toolbar)

        # --- Suporte a Guias ---
        self.tabs = QTabWidget() # Primeiro, inicialize o QTabWidget
        self.tabs.setDocumentMode(True) # Modo de documento (aparência mais moderna)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick) # Abrir nova aba ao clicar duas vezes
        self.tabs.currentChanged.connect(self.current_tab_changed) # Mudar URL na barra quando a aba muda

        self.setCentralWidget(self.tabs)

        # Agora que self.tabs existe e tem uma guia, podemos conectar os botões
        # Botões da barra de navegação
        back_btn = QAction("⬅️ Voltar", self)
        back_btn.setStatusTip("Voltar para a página anterior")
        back_btn.triggered.connect(lambda: self.current_browser().back()) # Conecta a uma lambda para chamar no clique
        self.toolbar.addAction(back_btn)

        forward_btn = QAction("➡️ Avançar", self)
        forward_btn.setStatusTip("Avançar para a próxima página")
        forward_btn.triggered.connect(lambda: self.current_browser().forward()) # Conecta a uma lambda
        self.toolbar.addAction(forward_btn)

        reload_btn = QAction("🔄 Recarregar", self)
        reload_btn.setStatusTip("Recarregar a página atual")
        reload_btn.triggered.connect(lambda: self.current_browser().reload()) # Conecta a uma lambda
        self.toolbar.addAction(reload_btn)

        home_btn = QAction("🏠 Início", self)
        home_btn.setStatusTip("Ir para a página inicial")
        home_btn.triggered.connect(self.navigate_home) # Essa já estava OK
        self.toolbar.addAction(home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        # Botão para adicionar nova guia
        new_tab_btn = QAction("➕ Nova Guia", self)
        new_tab_btn.setStatusTip("Abrir uma nova guia")
        new_tab_btn.triggered.connect(self.add_new_tab)
        self.toolbar.addAction(new_tab_btn)


        self.add_new_tab(QUrl("https://www.google.com"), "Página Inicial") # Adiciona a primeira guia
        # Após adicionar a primeira aba, garantimos que os botões sejam atualizados
        self.update_buttons_state()


        # Ocultar a barra de status por enquanto (pode ser adicionada depois se necessário)
        self.statusBar().hide()

    def current_browser(self):
        """Retorna a instância do navegador da guia atual."""
        # Garante que sempre haja um widget antes de tentar acessá-lo
        if self.tabs.count() > 0:
            return self.tabs.currentWidget()
        return None # Retorna None se não houver abas (embora sempre teremos uma)

    def add_new_tab(self, qurl=None, label="Nova Guia"):
        """Adiciona uma nova guia ao navegador."""
        if qurl is None:
            qurl = QUrl("https://www.google.com") # Padrão para nova aba

        browser = BrowserTab()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        # Atualiza a URL na barra quando a página muda
        browser.urlChanged.connect(lambda qurl_obj, browser=browser: self.update_urlbar(qurl_obj, browser))
        browser.loadStarted.connect(lambda: self.update_buttons_state()) # Atualiza estado dos botões
        browser.loadFinished.connect(lambda success: self.update_buttons_state()) # Atualiza estado dos botões

        # Conectar o título da guia para ser o título da página
        browser.titleChanged.connect(lambda title, browser=browser: self.tabs.setTabText(self.tabs.indexOf(browser), title))


    def tab_open_doubleclick(self, index):
        """Abre uma nova guia ao dar clique duplo na barra de abas."""
        if index == -1: # Clicou em uma área vazia
            self.add_new_tab()

    def current_tab_changed(self, index):
        """Atualiza a barra de URL quando a guia ativa muda."""
        browser = self.current_browser()
        if browser:
            qurl = browser.url()
            self.update_urlbar(qurl, browser)
            self.update_buttons_state() # Garante que os botões refletem a guia atual

    def navigate_home(self):
        """Volta para a página inicial."""
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        """
        Navega para a URL digitada, adiciona HTTPS por padrão
        ou faz uma pesquisa no Google.
        """
        url = self.url_bar.text()
        browser = self.current_browser()
        if not browser: # Se não houver navegador ativo, não faz nada
            return

        # 1. Adiciona https:// se não houver protocolo
        if not url.startswith("http://") and not url.startswith("https://"):
            # Verifica se parece um domínio (contém pelo menos um ponto)
            if "." in url and not " " in url: # Garante que não é uma frase com espaços
                url = "https://" + url # Tenta HTTPS por padrão
            else:
                # 2. Se não parecer uma URL, faz uma pesquisa no Google
                search_query = QUrl.toPercentEncoding(url)
                url = f"https://www.google.com/search?q={search_query}"

        browser.setUrl(QUrl(url))
        self.update_buttons_state() # Atualiza o estado dos botões após a navegação

    def update_urlbar(self, q, browser=None):
        """Atualiza a barra de URL com a URL da guia atual."""
        # Apenas atualiza se o navegador passado for o navegador atual ou se não houver um navegador específico
        if browser is None or browser == self.current_browser():
            self.url_bar.setText(q.toString())
            self.url_bar.setCursorPosition(0) # Volta o cursor para o início

    def update_buttons_state(self):
        """Atualiza o estado (habilitado/desabilitado) dos botões de navegação."""
        browser = self.current_browser()
        if browser:
            # Acessa o histórico para verificar se pode voltar/avançar
            history = browser.history()
            can_go_back = history.canGoBack()
            can_go_forward = history.canGoForward()
        else:
            # Se não houver navegador, desabilita tudo
            can_go_back = False
            can_go_forward = False

        for action in self.toolbar.actions():
            if action.text() == "⬅️ Voltar":
                # Habilita "Voltar" se houver um navegador, puder voltar e não estiver na página inicial
                action.setEnabled(browser is not None and can_go_back and browser.url() != QUrl("https://www.google.com"))
            elif action.text() == "➡️ Avançar":
                action.setEnabled(browser is not None and can_go_forward)
            elif action.text() == "🔄 Recarregar":
                action.setEnabled(browser is not None) # Recarregar sempre que houver um navegador
            elif action.text() == "🏠 Início":
                action.setEnabled(browser is not None) # Home sempre que houver um navegador
            elif action.text() == "➕ Nova Guia":
                action.setEnabled(True) # Nova guia sempre habilitada


# Função principal para rodar o aplicativo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Navegador Py-Tech") # Define o nome da aplicação para o sistema
    navegador = MiniNavegador()
    navegador.show()
    sys.exit(app.exec_())
