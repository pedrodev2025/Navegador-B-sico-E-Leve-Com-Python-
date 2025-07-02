import sys
import os
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QTabWidget,
    QProgressBar, QAction, QDialog, QVBoxLayout, QPushButton,
    QLabel, QInputDialog, QListWidget, QListWidgetItem, QHBoxLayout
)
from PyQt6.QtGui import QAction # Re-importar para garantir, embora já esteja lá
from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile

# Diretório base onde todos os perfis serão armazenados
BASE_PROFILES_DIR = os.path.join(os.path.expanduser("~"), ".config", "navegador_pytech_profiles")

class ProfileSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Perfil")
        self.setGeometry(300, 300, 400, 300)
        self.selected_profile_name = None
        self.profile_path = None

        self.init_ui()
        self.load_profiles()

    def init_ui(self):
        layout = QVBoxLayout()

        label = QLabel("Escolha um perfil ou crie um novo:")
        layout.addWidget(label)

        self.profile_list_widget = QListWidget()
        self.profile_list_widget.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.profile_list_widget)

        button_layout = QHBoxLayout()
        self.create_profile_btn = QPushButton("Criar Novo Perfil")
        self.create_profile_btn.clicked.connect(self.create_new_profile)
        button_layout.addWidget(self.create_profile_btn)

        self.select_profile_btn = QPushButton("Abrir Perfil Selecionado")
        self.select_profile_btn.clicked.connect(self.accept_selection)
        self.select_profile_btn.setEnabled(False) # Desabilitado até um item ser selecionado
        button_layout.addWidget(self.select_profile_btn)

        # Conectar para habilitar/desabilitar o botão de seleção
        self.profile_list_widget.itemSelectionChanged.connect(self.toggle_select_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_select_button(self):
        self.select_profile_btn.setEnabled(len(self.profile_list_widget.selectedItems()) > 0)

    def load_profiles(self):
        self.profile_list_widget.clear()
        
        # Adicionar o modo Convidado
        guest_item = QListWidgetItem("Convidado (Não Salva Dados)")
        guest_item.setData(Qt.ItemDataRole.UserRole, "guest")
        self.profile_list_widget.addItem(guest_item)

        # Carregar perfis permanentes
        os.makedirs(BASE_PROFILES_DIR, exist_ok=True)
        for profile_dir in os.listdir(BASE_PROFILES_DIR):
            full_path = os.path.join(BASE_PROFILES_DIR, profile_dir)
            if os.path.isdir(full_path):
                profile_item = QListWidgetItem(profile_dir)
                profile_item.setData(Qt.ItemDataRole.UserRole, profile_dir)
                self.profile_list_widget.addItem(profile_item)
        
        # Selecionar o modo Convidado por padrão
        self.profile_list_widget.setCurrentItem(guest_item)


    def create_new_profile(self):
        name, ok = QInputDialog.getText(self, "Novo Perfil", "Nome do novo perfil:")
        if ok and name:
            name = name.strip()
            if not name:
                return # Não criar perfil com nome vazio
            profile_dir = os.path.join(BASE_PROFILES_DIR, name)
            if os.path.exists(profile_dir):
                # Mensagem de erro simples, poderia ser um QMessageBox
                QMessageBox.warning(self, "Erro", "Perfil com este nome já existe.")
                return

            os.makedirs(profile_dir, exist_ok=True)
            self.load_profiles() # Recarrega a lista para mostrar o novo perfil
            # Seleciona o novo perfil na lista
            for i in range(self.profile_list_widget.count()):
                item = self.profile_list_widget.item(i)
                if item.text() == name:
                    self.profile_list_widget.setCurrentItem(item)
                    break


    def accept_selection(self):
        selected_items = self.profile_list_widget.selectedItems()
        if selected_items:
            self.selected_profile_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.accept()

# As classes BrowserTab e MiniNavegador precisam ser ajustadas para usar o perfil selecionado.
# A classe BrowserTab agora recebe um objeto QWebEngineProfile
class BrowserTab(QWebEngineView):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setPage(QWebEngineView().page()) # Cria uma nova página para associar o perfil
        self.page().setProfile(profile) # Associa o perfil à página
        self.load(QUrl("https://www.google.com")) # Página inicial padrão para cada nova guia

class MiniNavegador(QMainWindow):
    def __init__(self, selected_profile_name="guest"):
        super().__init__()

        self.setWindowTitle("Navegador Py-Tech")
        self.resize(1200, 800)

        # --- Configuração do Perfil de Navegação ---
        self.profile = self.get_or_create_profile(selected_profile_name)

        # Barra de navegação (Toolbar)
        self.toolbar = QToolBar("Navegação")
        self.addToolBar(self.toolbar)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.toolbar.addWidget(self.progress_bar)

        # --- Suporte a Guias ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)

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
        
        # Botão para trocar ou criar perfil (NOVO)
        profile_btn = QAction(f"👤 {selected_profile_name}", self)
        profile_btn.setStatusTip("Gerenciar perfis")
        profile_btn.triggered.connect(self.show_profile_selector)
        self.toolbar.addAction(profile_btn)
        self.profile_action_button = profile_btn # Salvar referência para atualizar texto

        # Adiciona a primeira aba com o perfil selecionado
        self.add_new_tab(QUrl("https://www.google.com"), "Página Inicial")
        self.update_buttons_state()

        self.statusBar().hide()
    
    def get_or_create_profile(self, profile_name):
        if profile_name == "guest":
            # Perfil convidado não persistente
            return QWebEngineProfile("GuestProfile", self) # Sem path de persistência
        else:
            # Perfil persistente para o usuário
            profile_path = os.path.join(BASE_PROFILES_DIR, profile_name)
            os.makedirs(profile_path, exist_ok=True)
            profile = QWebEngineProfile(profile_name, self)
            profile.setPersistentStoragePath(profile_path)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
            return profile

    def show_profile_selector(self):
        # Implementação simples para mostrar o seletor novamente,
        # mas para trocar o perfil em tempo de execução, seria mais complexo
        # envolvendo fechar e reabrir o navegador com o novo perfil.
        # Por simplicidade, este botão pode simplesmente reabrir o seletor,
        # e o usuário precisaria reiniciar o navegador para que a troca de perfil tenha efeito completo.
        # Ou você pode implementar uma lógica para reiniciar a aplicação aqui.
        print("Botão de perfil clicado. Reinicie o navegador para trocar de perfil.")
        # Se quiser fazer a troca dinâmica, precisaria recriar a QApplication e o MiniNavegador
        # que é mais complexo em PyQt. Uma forma mais simples é fechar e pedir para o usuário reiniciar.
        # Ou, idealmente, você criaria uma nova janela do navegador com o perfil selecionado.
        
        dialog = ProfileSelectorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_name = dialog.selected_profile_name
            if selected_name and selected_name != self.profile.name(): # Se um novo perfil foi selecionado
                print(f"Novo perfil selecionado: {selected_name}. Por favor, reinicie o navegador para aplicar.")
                # Opção 1: Mensagem e Reiniciar Manualmente
                QMessageBox.information(self, "Trocar Perfil", 
                                        f"Você selecionou o perfil '{selected_name}'.\n"
                                        "Por favor, feche e reabra o navegador para usar este perfil.")
                # Opção 2: Reiniciar a Aplicação Programaticamente (mais complexo)
                # self.close()
                # self.app.exit(0) # Termina a aplicação atual
                # sys.exit(0) # Sai do script

    def current_browser(self):
        if self.tabs.count() > 0:
            return self.tabs.currentWidget()
        return None

    def add_new_tab(self, qurl=None, label="Nova Guia"):
        if qurl is None or isinstance(qurl, bool):
            qurl = QUrl("https://www.google.com")

        browser = BrowserTab(self.profile) # Passa o perfil configurado
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl_obj, browser=browser: self.update_urlbar(qurl_obj, browser))
        browser.loadStarted.connect(lambda: self.update_buttons_state())
        browser.loadFinished.connect(lambda success: self.update_buttons_state())
        browser.loadProgress.connect(self.update_progress_bar)

        browser.titleChanged.connect(lambda title, browser=browser: self.tabs.setTabText(self.tabs.indexOf(browser), title))

    def tab_open_doubleclick(self, index):
        if index == -1:
            self.add_new_tab()

    def current_tab_changed(self, index):
        browser = self.current_browser()
        if browser:
            qurl = browser.url()
            self.update_urlbar(qurl, browser)
            self.update_buttons_state()

    def navigate_home(self):
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        url = self.url_bar.text()
        browser = self.current_browser()
        if not browser:
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            if "." in url and not " " in url:
                url = "https://" + url
            else:
                search_query_bytes = QUrl.toPercentEncoding(url)
                search_query_str = search_query_bytes.data().decode('utf-8')
                url = f"https://www.google.com/search?q={search_query_str}"

        browser.setUrl(QUrl(url))
        self.update_buttons_state()

    def update_urlbar(self, q, browser=None):
        if browser is None or browser == self.current_browser():
            self.url_bar.setText(q.toString())
            self.url_bar.setCursorPosition(0)

    def update_buttons_state(self):
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
                action.setEnabled(browser is not None and can_go_back)
            elif action.text() == "➡️ Avançar":
                action.setEnabled(browser is not None and can_go_forward)
            elif action.text() == "🔄 Recarregar":
                action.setEnabled(browser is not None)
            elif action.text() == "🏠 Início":
                action.setEnabled(browser is not None)
            elif action.text() == "➕ Nova Guia":
                action.setEnabled(True)
        # Atualiza o nome do perfil no botão
        self.profile_action_button.setText(f"👤 {self.profile.name()}")


    def update_progress_bar(self, progress):
        if progress < 100 and progress > 0:
            self.progress_bar.setValue(progress)
            self.progress_bar.setVisible(True)
        elif progress == 100:
            self.progress_bar.setVisible(False)
        else: # progress == 0 (quando o carregamento começa)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setApplicationName("Navegador Py-Tech")

    # Mostrar o seletor de perfil primeiro
    profile_dialog = ProfileSelectorDialog()
    if profile_dialog.exec() == QDialog.DialogCode.Accepted:
        selected_profile = profile_dialog.selected_profile_name
        navegador = MiniNavegador(selected_profile)
        navegador.show()
        sys.exit(app.exec())
    else:
        # Se o usuário cancelar o diálogo de seleção de perfil, sair da aplicação
        sys.exit(0)
