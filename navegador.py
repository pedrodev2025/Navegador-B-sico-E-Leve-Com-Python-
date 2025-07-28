import sys
import os
import shutil
import gc
import glob
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QWidget,
    QVBoxLayout, QMessageBox, QInputDialog, QDialog, QPushButton, QListWidget,
    QHBoxLayout, QLabel, QAction, QTabWidget, QMenu # Importe QTabWidget e QMenu
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QDir, QStandardPaths, QTimer, QThread
from PyQt5.QtGui import QIcon, QKeySequence # Importe QKeySequence

# --- Definições de Caminho e Configurações ---
APP_DATA_DIR_NAME = "navegadorpytech"
PROFILES_DIR_NAME = "profiles"
DEFAULT_HOME_URL = "https://www.google.com"
DEFAULT_SEARCH_ENGINE_URL = "https://www.google.com/search?q="

def get_app_base_data_dir():
    user_home = os.path.expanduser('~')
    app_data_path = os.path.join(user_home, 'AppData', 'Local', APP_DATA_DIR_NAME)
    os.makedirs(app_data_path, exist_ok=True)
    return app_data_path

def get_profiles_data_dir():
    profiles_path = os.path.join(get_app_base_data_dir(), PROFILES_DIR_NAME)
    os.makedirs(profiles_path, exist_ok=True)
    return profiles_path

def get_profile_data_path(profile_name):
    profile_data_path = os.path.join(get_profiles_data_dir(), profile_name)
    os.makedirs(profile_data_path, exist_ok=True)
    return profile_data_path

def get_guest_profile_base_temp_dir():
    temp_base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
    guest_temp_path = os.path.join(temp_base_dir, f"{APP_DATA_DIR_NAME}_guest_{os.getpid()}")
    os.makedirs(guest_temp_path, exist_ok=True)
    return guest_temp_path

# --- CLASSE PARA EXCLUSÃO EM SEGUNDO PLANO ---
class CleanerThread(QThread):
    def __init__(self, path_to_clean):
        super().__init__()
        self.path_to_clean = path_to_clean
        self.max_retries = 30
        self.retry_delay = 1000

    def run(self):
        print(f"Iniciando limpeza em segundo plano para: {self.path_to_clean}")
        for i in range(self.max_retries):
            if not os.path.exists(self.path_to_clean):
                print(f"Diretório temporário {self.path_to_clean} já não existe. Limpeza concluída (ou já foi feita).")
                return

            try:
                shutil.rmtree(self.path_to_clean)
                print(f"Dados do modo convidado apagados de: {self.path_to_clean}")
                return
            except OSError as e:
                print(f"Tentativa {i+1}/{self.max_retries}: Erro ao apagar dados do modo convidado em {self.path_to_clean}: {e}")
                if i < self.max_retries - 1:
                    self.msleep(self.retry_delay)
                else:
                    print(f"Falha CRÍTICA e PERSISTENTE: Não foi possível apagar dados do modo convidado em {self.path_to_clean} após {self.max_retries} tentativas. Por favor, remova manualmente se desejar.")

def clean_guest_profile_data_async(path):
    if os.path.exists(path) and os.path.isdir(path):
        cleaner = CleanerThread(path)
        cleaner.start()
        return cleaner
    else:
        print(f"Caminho para limpeza não é um diretório ou não existe: {path}")
        return None

def clean_all_old_guest_data_on_startup():
    temp_base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
    guest_dir_pattern = os.path.join(temp_base_dir, f"{APP_DATA_DIR_NAME}_guest_*")
    
    print("\nVerificando e limpando dados de convidados anteriores na inicialização...")
    
    found_old_dirs = False
    for path in glob.glob(guest_dir_pattern):
        current_session_pid_match = re.search(r'_guest_(\d+)$', path)
        if current_session_pid_match and int(current_session_pid_match.group(1)) == os.getpid():
            print(f"  Pulando diretório da sessão atual: {path}")
            continue

        if os.path.isdir(path):
            found_old_dirs = True
            print(f"  Tentando limpar diretório antigo: {path}")
            try:
                shutil.rmtree(path)
                print(f"  Diretório antigo apagado com sucesso: {path}")
            except OSError as e:
                print(f"  AVISO: Não foi possível apagar diretório antigo {path}: {e}")
    
    if not found_old_dirs:
        print("  Nenhum dado de convidado antigo encontrado para limpeza.")
    print("Fim da verificação de limpeza na inicialização.\n")


class ProfileSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Perfil")
        self.setGeometry(200, 200, 400, 350)
        
        self.selected_profile = None

        layout = QVBoxLayout(self)

        self.profile_list_widget = QListWidget()
        layout.addWidget(self.profile_list_widget)

        button_layout = QHBoxLayout()

        self.guest_button = QPushButton("Iniciar no Modo Convidado")
        self.guest_button.clicked.connect(self.select_guest_mode)
        button_layout.addWidget(self.guest_button)

        self.create_button = QPushButton("Criar Novo Perfil")
        self.create_button.clicked.connect(self.create_new_profile)
        button_layout.addWidget(self.create_button)

        layout.addLayout(button_layout)

        action_button_layout = QHBoxLayout()

        self.ok_button = QPushButton("Carregar Perfil Selecionado")
        self.ok_button.clicked.connect(self.accept_selection)
        self.ok_button.setEnabled(False)
        action_button_layout.addWidget(self.ok_button)

        self.delete_button = QPushButton("Deletar Perfil Selecionado")
        self.delete_button.clicked.connect(self.delete_selected_profile)
        self.delete_button.setEnabled(False)
        action_button_layout.addWidget(self.delete_button)

        layout.addLayout(action_button_layout)

        self.load_profiles()
        self.profile_list_widget.itemDoubleClicked.connect(self.accept_selection)
        self.profile_list_widget.itemClicked.connect(self.enable_buttons)

        self.enable_buttons()

    def load_profiles(self):
        self.profile_list_widget.clear()
        profiles_dir = get_profiles_data_dir()
        existing_profiles = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
        
        if not existing_profiles:
            QMessageBox.information(self, "Nenhum Perfil Encontrado", 
                                    "Nenhum perfil persistente encontrado. Você pode criar um novo ou iniciar no modo convidado.")
            self.profile_list_widget.setEnabled(False)
            self.ok_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.profile_list_widget.setEnabled(True)
            for profile in existing_profiles:
                self.profile_list_widget.addItem(profile)
            if existing_profiles:
                self.profile_list_widget.setCurrentRow(0)
                self.enable_buttons()

    def enable_buttons(self):
        is_selected = bool(self.profile_list_widget.currentItem())
        self.ok_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)

    def select_guest_mode(self):
        self.selected_profile = "guest_mode"
        self.accept()

    def create_new_profile(self):
        new_profile_name, ok = QInputDialog.getText(
            self, "Novo Perfil", "Digite o nome para o novo perfil:"
        )
        if ok and new_profile_name:
            new_profile_name = new_profile_name.strip()
            if not new_profile_name:
                QMessageBox.warning(self, "Nome Inválido", "O nome do perfil não pode ser vazio.")
                return
            
            if new_profile_name.lower() == "guest" or new_profile_name.lower() == "guest_mode":
                QMessageBox.warning(self, "Nome Reservado", "O nome 'guest' é reservado para o modo convidado. Por favor, escolha outro nome.")
                return

            profile_path = get_profile_data_path(new_profile_name)
            if os.path.exists(profile_path) and os.path.isdir(profile_path):
                QMessageBox.information(self, "Perfil Existente", f"O perfil '{new_profile_name}' já existe e será carregado.")
            else:
                QMessageBox.information(self, "Perfil Criado", f"O perfil '{new_profile_name}' foi criado com sucesso!")

            self.selected_profile = new_profile_name
            self.accept()

    def accept_selection(self):
        selected_item = self.profile_list_widget.currentItem()
        if selected_item:
            self.selected_profile = selected_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "Nenhuma Seleção", "Por favor, selecione um perfil ou inicie no modo convidado.")

    def delete_selected_profile(self):
        selected_item = self.profile_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Nenhuma Seleção", "Por favor, selecione um perfil para deletar.")
            return

        profile_to_delete = selected_item.text()
        reply = QMessageBox.question(self, 'Confirmar Exclusão', 
                                    f"Tem certeza que deseja deletar o perfil '{profile_to_delete}' e todos os seus dados?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            profile_path = get_profile_data_path(profile_to_delete)
            if os.path.exists(profile_path):
                try:
                    shutil.rmtree(profile_path)
                    QMessageBox.information(self, "Perfil Deletado", f"O perfil '{profile_to_delete}' foi deletado com sucesso.")
                    self.load_profiles()
                except OSError as e:
                    QMessageBox.critical(self, "Erro ao Deletar", f"Erro ao deletar o perfil '{profile_to_delete}':\n{e}")
            else:
                QMessageBox.warning(self, "Erro", "Diretório do perfil não encontrado.")


# --- NOVA CLASSE PARA CADA ABA DO NAVEGADOR ---
class BrowserTabWidget(QWidget):
    def __init__(self, profile, parent=None, initial_url=None):
        super().__init__(parent)
        self.web_profile = profile # Recebe o perfil de QWebEngineProfile
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # Remove margens extras

        self.browser = QWebEngineView(self)
        self.browser.setPage(QWebEnginePage(self.web_profile, self.browser)) # Associa a página ao perfil

        layout.addWidget(self.browser)

        # Conecta sinais para atualizar a janela principal
        self.browser.urlChanged.connect(self._url_changed)
        self.browser.titleChanged.connect(self._title_changed)
        self.browser.loadFinished.connect(self._load_finished)

        # Carrega a URL inicial
        if initial_url:
            self.browser.setUrl(QUrl(initial_url))
        else:
            self.browser.setUrl(QUrl(DEFAULT_HOME_URL))

    def _url_changed(self, qurl):
        # Sinaliza para a janela principal que a URL mudou
        if self.parent() and hasattr(self.parent(), 'tab_url_changed'):
            self.parent().tab_url_changed(self.browser.url())

    def _title_changed(self, title):
        # Sinaliza para a janela principal que o título mudou
        if self.parent() and hasattr(self.parent(), 'tab_title_changed'):
            self.parent().tab_title_changed(title)

    def _load_finished(self, success):
        # Sinaliza para a janela principal que o carregamento terminou (útil para icones, etc)
        if self.parent() and hasattr(self.parent(), 'tab_load_finished'):
            self.parent().tab_load_finished(success)


class Browser(QMainWindow):
    def __init__(self, profile_name="guest_mode", initial_url=DEFAULT_HOME_URL):
        super().__init__()
        self.profile_name = profile_name
        self.is_guest_mode = (self.profile_name == "guest_mode")
        self.guest_temp_path = None
        self._cleaner_thread = None

        # 1. Configura o QWebEngineProfile PRIMEIRO
        if self.is_guest_mode:
            self.guest_temp_path = get_guest_profile_base_temp_dir()
            print(f"Iniciando em modo convidado. Dados temporários em: {self.guest_temp_path}")

            guest_cache_path = os.path.join(self.guest_temp_path, "cache")
            guest_storage_path = os.path.join(self.guest_temp_path, "storage")
            os.makedirs(guest_cache_path, exist_ok=True)
            os.makedirs(guest_storage_path, exist_ok=True)
            
            self.web_profile = QWebEngineProfile("guest_profile", self)
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            self.web_profile.setCachePath(guest_cache_path)
            self.web_profile.setPersistentStoragePath(guest_storage_path)
            self._guest_web_profile_ref = self.web_profile 
        else:
            profile_data_path = get_profile_data_path(self.profile_name)
            self.web_profile = QWebEngineProfile(self.profile_name, self) 
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
            self.web_profile.setCachePath(profile_data_path)
            self.web_profile.setPersistentStoragePath(profile_data_path)

        title_suffix = "Modo Convidado" if self.is_guest_mode else f"Perfil: {self.profile_name}"
        self.setWindowTitle(f"Mini Navegador PyQt - {title_suffix}")
        self.setGeometry(100, 100, 1024, 768)

        # Container principal
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)

        # 2. Sistema de Abas (QTabWidget) - Criado ANTES da Toolbar
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True) # Aparência mais moderna
        self.tabs.tabBarDoubleClicked.connect(self.add_new_tab) # Duplo clique na barra de abas cria nova aba
        self.tabs.currentChanged.connect(self.current_tab_changed) # Atualiza URL bar ao mudar de aba
        self.tabs.setTabsClosable(True) # Habilita o botão 'x' nas abas
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index) # Conecta o fechamento da aba

        layout.addWidget(self.tabs) # Adiciona o QTabWidget ao layout

        # 3. Barra de Ferramentas
        toolbar = QToolBar("Navegação")
        self.addToolBar(toolbar)

        # Conecta os botões a MÉTODOS DELEGADOS na classe Browser
        # Isso garante que self.current_browser_tab() só será chamado QUANDO o botão for clicado
        back_button = toolbar.addAction("Voltar")
        back_button.triggered.connect(self._go_back_on_current_tab) 

        forward_button = toolbar.addAction("Avançar")
        forward_button.triggered.connect(self._go_forward_on_current_tab) 

        reload_button = toolbar.addAction("Recarregar")
        reload_button.triggered.connect(self._reload_current_tab) 
        
        home_button = toolbar.addAction("Home")
        home_button.triggered.connect(self._go_home_on_current_tab) # Renomeado para consistência

        # Botão para nova aba
        new_tab_button = toolbar.addAction("Nova Aba")
        new_tab_button.triggered.connect(self.add_new_tab)
        new_tab_button.setShortcut(QKeySequence("Ctrl+T")) # Atalho para nova aba

        # Botão para fechar aba
        close_tab_button = toolbar.addAction("Fechar Aba")
        close_tab_button.triggered.connect(self.close_current_tab)
        close_tab_button.setShortcut(QKeySequence("Ctrl+W")) # Atalho para fechar aba

        manage_profiles_button = toolbar.addAction("Gerenciar Perfis")
        manage_profiles_button.triggered.connect(self.show_profile_management_dialog)

        self.url_bar_layout = QHBoxLayout()
        
        self.secure_icon = QLabel()
        self.secure_icon.setFixedSize(20, 20)
        self.secure_icon.setPixmap(QIcon.fromTheme("object-locked", QIcon.fromTheme("dialog-ok")).pixmap(20, 20))

        self.url_bar_layout.addWidget(self.secure_icon)
        
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url_from_bar) # Conectado a nova função
        self.url_bar_layout.addWidget(self.url_bar)

        toolbar.addWidget(self._create_widget_from_layout(self.url_bar_layout))

        # 4. Adiciona a primeira aba APÓS o QTabWidget ser inicializado
        self.add_new_tab(QUrl(initial_url))
        
        # Garante que os botões da toolbar estejam conectados corretamente após a primeira aba ser criada
        self.update_toolbar_connections() # Chama isso para a aba inicial

    def _create_widget_from_layout(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    # --- Novos Métodos Delegados para os botões da Toolbar ---
    def _go_back_on_current_tab(self):
        if self.current_browser_tab(): # Verifica se há uma aba ativa
            self.current_browser_tab().browser.back()

    def _go_forward_on_current_tab(self):
        if self.current_browser_tab():
            self.current_browser_tab().browser.forward()

    def _reload_current_tab(self):
        if self.current_browser_tab():
            self.current_browser_tab().browser.reload()

    def _go_home_on_current_tab(self):
        if self.current_browser_tab():
            self.current_browser_tab().browser.setUrl(QUrl(DEFAULT_HOME_URL))


    def add_new_tab(self, qurl_or_bool=False):
        """Adiciona uma nova aba ao navegador. Pode receber uma QUrl ou ser chamada por um sinal (bool)."""
        if isinstance(qurl_or_bool, QUrl):
            initial_url = qurl_or_bool
        else:
            initial_url = QUrl(DEFAULT_HOME_URL) # Se não for URL, é por clique no botão/duplo clique

        # Cria uma nova instância de BrowserTabWidget, passando o perfil
        browser_tab = BrowserTabWidget(self.web_profile, self, initial_url)
        
        # Adiciona a aba e a torna a aba ativa
        index = self.tabs.addTab(browser_tab, "Nova Aba")
        self.tabs.setCurrentIndex(index)

    def close_current_tab(self):
        """Fecha a aba atualmente ativa."""
        current_index = self.tabs.currentIndex()
        if self.tabs.count() > 1: # Não feche a última aba
            self.tabs.removeTab(current_index)
        else:
            self.close() # Se for a última aba, fecha a janela principal

    def close_tab_by_index(self, index):
        """Fecha uma aba dado seu índice (usado pelo botão 'x' da aba)."""
        if self.tabs.count() > 1: # Não feche a última aba
            self.tabs.removeTab(index)
        else:
            self.close() # Se for a última aba, fecha a janela principal

    def current_browser_tab(self):
        """Retorna a instância de BrowserTabWidget da aba ativa."""
        return self.tabs.currentWidget()

    def navigate_to_url_from_bar(self):
        """Navega para a URL digitada na barra de endereço da aba ativa."""
        text = self.url_bar.text().strip()
        if not text:
            return

        current_browser = self.current_browser_tab().browser
        
        if os.path.exists(text):
            url = QUrl.fromLocalFile(text)
            current_browser.setUrl(url)
        elif (text.startswith("http://") or
            text.startswith("https://") or
            text.startswith("ftp://") or
            ('.' in text and ' ' not in text)):
            
            if not (text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://")):
                url = "http://" + text
            else:
                url = text
            current_browser.setUrl(QUrl(url))
        else:
            search_query = QUrl.toPercentEncoding(text).data().decode('utf-8')
            search_url = DEFAULT_SEARCH_ENGINE_URL + search_query
            current_browser.setUrl(QUrl(search_url))

    def update_url_bar(self, qurl):
        # Esta função foi removida diretamente do browser.urlChanged.
        # Agora ela é chamada pela aba ativa através de `tab_url_changed`.
        pass

    def tab_url_changed(self, qurl):
        """Chamado quando a URL de uma aba muda."""
        # Se a aba que mudou for a aba ativa, atualiza a barra de URL principal
        if self.tabs.currentWidget() == self.sender(): # 'sender()' é a instância de BrowserTabWidget que emitiu o sinal
            if qurl.isLocalFile():
                self.url_bar.setText(qurl.toLocalFile())
            else:
                self.url_bar.setText(qurl.toString())
            self.update_security_icon(qurl)

    def tab_title_changed(self, title):
        """Chamado quando o título de uma aba muda."""
        # Atualiza o título da aba no QTabWidget
        index = self.tabs.indexOf(self.sender())
        if index != -1:
            self.tabs.setTabText(index, title or "Nova Aba") # Fallback para "Nova Aba" se o título for vazio

    def tab_load_finished(self, success):
        """Chamado quando uma aba termina de carregar."""
        # Você pode usar isso para mostrar/ocultar um spinner de carregamento, etc.
        # Por enquanto, apenas garante que o ícone de segurança seja atualizado.
        if self.tabs.currentWidget() == self.sender():
            self.update_security_icon(self.sender().browser.url())

    def current_tab_changed(self, index):
        """Chamado quando a aba ativa muda."""
        # Atualiza a barra de URL e o ícone de segurança para refletir a nova aba ativa
        if index != -1:
            current_tab_widget = self.tabs.widget(index)
            if current_tab_widget:
                current_url = current_tab_widget.browser.url()
                if current_url.isLocalFile():
                    self.url_bar.setText(current_url.toLocalFile())
                else:
                    self.url_bar.setText(current_url.toString())
                self.update_security_icon(current_url)
                self.tabs.setTabText(index, current_tab_widget.browser.title() or "Nova Aba")
                # Garante que os botões de navegação da toolbar estejam conectados ao browser correto
                self.update_toolbar_connections()
        
    def update_toolbar_connections(self):
        """Atualiza os alvos dos botões da toolbar para a aba ativa."""
        # Desconecta e reconecta os botões da toolbar para a aba atualmente ativa
        current_browser = self.current_browser_tab().browser
        
        # Percorre as ações da toolbar e atualiza suas conexões
        for action in self.findChildren(QAction):
            if action.text() == "Voltar":
                try:
                    action.triggered.disconnect()
                except TypeError: # Ignora se não houver conexão anterior
                    pass
                action.triggered.connect(current_browser.back)
            elif action.text() == "Avançar":
                try:
                    action.triggered.disconnect()
                except TypeError:
                    pass
                action.triggered.connect(current_browser.forward)
            elif action.text() == "Recarregar":
                try:
                    action.triggered.disconnect()
                except TypeError:
                    pass
                action.triggered.connect(current_browser.reload)
            elif action.text() == "Home":
                try:
                    action.triggered.disconnect()
                except TypeError:
                    pass
                action.triggered.connect(self._go_home_on_current_tab) # O Home button continua chamando o delegado

    def update_security_icon(self, qurl):
        """Atualiza o ícone de segurança com base na URL."""
        if qurl.scheme() == "https":
            self.secure_icon.setPixmap(QIcon.fromTheme("object-locked", QIcon.fromTheme("dialog-ok")).pixmap(20, 20))
            self.secure_icon.setToolTip("Conexão segura (HTTPS)")
        elif qurl.isLocalFile():
             self.secure_icon.setPixmap(QIcon.fromTheme("dialog-information", QIcon.fromTheme("dialog-information")).pixmap(20, 20))
             self.secure_icon.setToolTip("Arquivo local")
        else:
            self.secure_icon.setPixmap(QIcon.fromTheme("dialog-warning", QIcon.fromTheme("dialog-error")).pixmap(20, 20))
            self.secure_icon.setToolTip("Conexão não segura ou HTTP")

    def show_profile_management_dialog(self):
        dialog = ProfileSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_profile = dialog.selected_profile
            if new_profile:
                QMessageBox.information(self, "Reiniciar", 
                                        f"O navegador será reiniciado com o perfil '{new_profile}'.")
                QApplication.quit()

    def closeEvent(self, event):
        if self.is_guest_mode and self.guest_temp_path:
            print(f"Agendando limpeza do modo convidado para: {self.guest_temp_path}")
            
            # Limpa o cache e links visitados do perfil antes de fechar
            if self._guest_web_profile_ref:
                self._guest_web_profile_ref.clearHttpCache()
                self._guest_web_profile_ref.clearAllVisitedLinks()
                # Libera a referência ao perfil para que o coletor de lixo possa atuar
                self._guest_web_profile_ref = None 
                print("Referências ao QWebEngineProfile do modo convidado liberadas.")

            gc.collect() 
            QTimer.singleShot(5000, lambda: self._start_cleaner_thread())
            
        super().closeEvent(event)

    def _start_cleaner_thread(self):
        self._cleaner_thread = clean_guest_profile_data_async(self.guest_temp_path)

if __name__ == "__main__":
    clean_all_old_guest_data_on_startup()

    app = QApplication(sys.argv)

    profile_to_load = "guest_mode"
    initial_load_url = DEFAULT_HOME_URL

    if len(sys.argv) > 1:
        file_path_from_arg = sys.argv[1]
        if os.path.exists(file_path_from_arg) and file_path_from_arg.lower().endswith(('.html', '.htm')):
            initial_load_url = QUrl.fromLocalFile(file_path_from_arg).toString()
            print(f"Iniciando com arquivo local: {file_path_from_arg}")
        else:
            print(f"Argumento inválido ou arquivo não HTML: {file_path_from_arg}")

    profiles_dir = get_profiles_data_dir()
    existing_profiles = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    profiles_exist = bool(existing_profiles)

    if profiles_exist:
        dialog = ProfileSelectionDialog()
        if dialog.exec_() == QDialog.Accepted:
            profile_to_load = dialog.selected_profile
        else:
            QMessageBox.information(None, "Nenhum Perfil Selecionado", 
                                    "Nenhum perfil persistente foi selecionado. Iniciando no modo convidado.")
            profile_to_load = "guest_mode"
    else:
        QMessageBox.information(None, "Iniciando em Modo Convidado", 
                                "Nenhum perfil persistente encontrado. Iniciando no modo convidado.\n"
                                "Você pode criar um novo perfil usando a opção 'Gerenciar Perfis'.")
        profile_to_load = "guest_mode"

    browser_window = Browser(profile_to_load, initial_url=initial_load_url)
    browser_window.show()

    sys.exit(app.exec_())
