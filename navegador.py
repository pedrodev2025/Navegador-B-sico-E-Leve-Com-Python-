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

        # Botões da barra de navegação
        back_btn = QAction("⬅️ Voltar", self)
        back_btn.setStatusTip("Voltar para a página anterior")
        back_btn.triggered.connect(self.current_browser().back)
        self.toolbar.addAction(back_btn)

        forward_btn = QAction("➡️ Avançar", self)
        forward_btn.setStatusTip("Avançar para a próxima página")
        forward_btn.triggered.connect(self.current_browser().forward)
        self.toolbar.addAction(forward_btn)

        reload_btn = QAction("🔄 Recarregar", self)
        reload_btn.setStatusTip("Recarregar a página atual")
        reload_btn.triggered.connect(self.current_browser().reload)
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
        new_tab_btn.triggered.connect(self.add_new_tab)
        self.toolbar.addAction(new_tab_btn)

        # --- Suporte a Guias ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True) # Modo de documento (aparência mais moderna)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick) # Abrir nova aba ao clicar duas vezes
        self.tabs.currentChanged.connect(self.current_tab_changed) # Mudar URL na barra quando a aba muda

        self.setCentralWidget(self.tabs)

        self.add_new_tab(QUrl("https://www.google.com"), "Página Inicial") # Adiciona a primeira guia

        # Ocultar a barra de status por enquanto (pode ser adicionada depois se necessário)
        self.statusBar().hide()

    def current_browser(self):
        """Retorna a instância do navegador da guia atual."""
        return self.tabs.currentWidget()

    def add_new_tab(self, qurl=None, label="Nova Guia"):
        """Adiciona uma nova guia ao navegador."""
        if qurl is None:
            qurl = QUrl("https://www.google.com") # Padrão para nova aba

        browser = BrowserTab()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        # Atualiza a URL na barra quando a página muda
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadStarted.connect(lambda: self.update_buttons_state()) # Atualiza estado dos botões
        browser.loadFinished.connect(lambda success: self.update_buttons_state()) # Atualiza estado dos botões

    def tab_open_doubleclick(self, index):
        """Abre uma nova guia ao dar clique duplo na barra de abas."""
        if index == -1: # Clicou em uma área vazia
            self.add_new_tab()

    def current_tab_changed(self, index):
        """Atualiza a barra de URL quando a guia ativa muda."""
        qurl = self.current_browser().url()
        self.update_urlbar(qurl, self.current_browser())
        self.update_buttons_state() # Garante que os botões refletem a guia atual

    def navigate_home(self):
        """Volta para a página inicial."""
        self.current_browser().setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        """
        Navega para a URL digitada, adiciona HTTPS por padrão
        ou faz uma pesquisa no Google.
        """
        url = self.url_bar.text()

        # 1. Adiciona https:// se não houver protocolo
        if not url.startswith("http://") and not url.startswith("https://"):
            # Verifica se parece um domínio (contém pelo menos um ponto)
            if "." in url and not " " in url:
                url = "https://" + url # Tenta HTTPS por padrão
            else:
                # 2. Se não parecer uma URL, faz uma pesquisa no Google
                search_query = QUrl.toPercentEncoding(url)
                url = f"https://www.google.com/search?q={search_query}"

        self.current_browser().setUrl(QUrl(url))
        self.update_buttons_state() # Atualiza o estado dos botões após a navegação

    def update_urlbar(self, q, browser=None):
        """Atualiza a barra de URL com a URL da guia atual."""
        if browser != self.current_browser():
            # Impede que URLs de guias em segundo plano atualizem a barra principal
            return

        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0) # Volta o cursor para o início

    def update_buttons_state(self):
        """Atualiza o estado (habilitado/desabilitado) dos botões de navegação."""
        browser = self.current_browser()
        if browser:
            # Encontra as ações na toolbar para atualizá-las
            for action in self.toolbar.actions():
                if action.text() == "⬅️ Voltar":
                    action.setEnabled(browser.url() != QUrl("https://www.google.com") and browser.canGoBack())
                elif action.text() == "➡️ Avançar":
                    action.setEnabled(browser.canGoForward())
        else:
            # Desabilita todos os botões se não houver navegador ativo
            for action in self.toolbar.actions():
                action.setEnabled(False)

# Função principal para rodar o aplicativo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Navegador Py-Tech") # Define o nome da aplicação para o sistema
    navegador = MiniNavegador()
    navegador.show()
    sys.exit(app.exec_())
