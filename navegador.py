import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *

class MiniNavegador(QMainWindow):
    def __init__(self):
        super().__init__()

        # Inicializa o navegador
        self.browser = QWebEngineView()

        # Definindo a página inicial
        self.browser.setUrl(QUrl("http://www.google.com"))

        # Barra de navegação
        self.url_bar = QLineEdit(self)
        self.url_bar.returnPressed.connect(self.navigate_to_url)

        # Botões de navegação
        self.back_button = QPushButton("Voltar", self)
        self.forward_button = QPushButton("Avançar", self)
        self.refresh_button = QPushButton("Atualizar", self)

        # Conectar os botões às funções
        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.refresh_button.clicked.connect(self.refresh_page)

        # Layout dos botões
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.forward_button)
        button_layout.addWidget(self.refresh_button)

        # Layout principal
        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.url_bar)
        layout.addWidget(self.browser)

        # Configuração do widget central
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Ajusta o tamanho da janela
        self.setWindowTitle("Mini Navegador")
        self.resize(1024, 768)

        # Conectar barra de URL à mudança de página
        self.browser.urlChanged.connect(self.update_url)

    def navigate_to_url(self):
        url = self.url_bar.text()
        self.browser.setUrl(QUrl(url))

    def update_url(self, q):
        self.url_bar.setText(q.toString())

    def go_back(self):
        """Voltar para a página anterior."""
        if self.browser.canGoBack():
            self.browser.back()

    def go_forward(self):
        """Avançar para a próxima página."""
        if self.browser.canGoForward():
            self.browser.forward()

    def refresh_page(self):
        """Atualizar a página atual."""
        self.browser.reload()

# Função principal para rodar o aplicativo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    navegador = MiniNavegador()
    navegador.show()
    sys.exit(app.exec_())
