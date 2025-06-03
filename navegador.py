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
        back_btn.triggered.connect(lambda: self.current_browser().back())
        self.toolbar.addAction(back_btn)

        forward_btn = QAction("➡️ Avançar", self)
        forward_btn.setStatusTip("Avançar para a próxima página")
        forward_btn.triggered.connect(lambda: self.current_browser().forward())
        self.toolbar.addAction(forward_btn)

        reload_btn = QAction("🔄 Recarregar", self)
        reload_btn.setStatusTip("Recarregar a página atual")
        reload_btn.triggered.connect(lambda: self.current_browser().reload())
        self.toolbar.addAction(reload_btn)

        home_btn = QAction("🏠 Início", self)
        home_btn.setStatusTip("Ir para a página inicial")
        home_btn.triggered.connect(self.navigate_home)
        self.toolbar.addAction(home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)

        # Botão para adicionar nova guia
        new_tab_btn = QAction("➕ Nova Guia", self)
        new_tab_btn.setStatusTip("Abrir uma nova guia")
        new_tab_btn.triggered.connect(lambda: self.add_new_tab())
        self.toolbar.addAction(new_tab_btn)


        self.add_new_tab(QUrl("https://www.google.com"), "Página Inicial")
        self.update_buttons_state()


        self.statusBar().hide()

    def current_browser(self):
        """Retorna a instância do navegador da guia atual."""
        if self.tabs.count() > 0:
            return self.tabs.currentWidget()
        return None

    def add_new_tab(self, qurl=None, label="Nova Guia"):
        """Adiciona uma nova guia ao navegador."""
        if qurl is None or isinstance(qurl, bool):
            qurl = QUrl("https://www.google.com")

        browser = BrowserTab()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl_obj, browser=browser: self.update_urlbar(qurl_obj, browser))
        browser.loadStarted.connect(lambda: self.update_buttons_state())
        browser.loadFinished.connect(lambda success: self.update_buttons_state())

        browser.titleChanged.connect(lambda title, browser=browser: self.tabs.setTabText(self.tabs.indexOf(browser), title))


    def tab_open_doubleclick(self, index):
        """Abre uma nova guia ao dar clique duplo na barra de abas."""
        if index == -1:
            self.add_new_tab()

    def current_tab_changed(self, index):
        """Atualiza a barra de URL quando a guia ativa muda."""
        browser = self.current_browser()
        if browser:
            qurl = browser.url()
            self.update_urlbar(qurl, browser)
            self.update_buttons_state()

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
        if not browser:
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            if "." in url and not " " in url:
                url = "https://" + url
            else:
                # --- AQUI ESTÁ A CORREÇÃO ---
                # Codifica o termo de busca para bytes e depois o decodifica para string normal antes de usar
                search_query_bytes = QUrl.toPercentEncoding(url)
                search_query_str = search_query_bytes.data().decode('utf-8') # Converte QByteArray para string UTF-8
                url = f"https://www.google.com/search?q={search_query_str}"
                # ----------------------------

        browser.setUrl(QUrl(url))
        self.update_buttons_state()

    def update_urlbar(self, q, browser=None):
        """Atualiza a barra de URL com a URL da guia atual."""
        if browser is None or browser == self.current_browser():
            self.url_bar.setText(q.toString())
            self.url_bar.setCursorPosition(0)

    def update_buttons_state(self):
        """Atualiza o estado (habilitado/desabilitado) dos botões de navegação."""
        browser = self.current_browser()
        if browser:
            history = browser.history()
            can_go_back = history.canGoBack()
            can_go_forward = history.canGoForward()
        else:
            can_go_back = False
            can_go_forward = False

        for action in self.toolbar.actions():
            if action.text() == "⬅️ Voltar":
                action.setEnabled(browser is not None and can_go_back and browser.url() != QUrl("https://www.google.com"))
            elif action.text() == "➡️ Avançar":
                action.setEnabled(browser is not None and can_go_forward)
            elif action.text() == "🔄 Recarregar":
                action.setEnabled(browser is not None)
            elif action.text() == "🏠 Início":
                action.setEnabled(browser is not None)
            elif action.text() == "➕ Nova Guia":
                action.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Navegador Py-Tech")
    navegador = MiniNavegador()
    navegador.show()
    sys.exit(app.exec_())
