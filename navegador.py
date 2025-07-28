import sys
import os
import shutil
import gc
import glob
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QWidget,
    QVBoxLayout, QMessageBox, QInputDialog, QDialog, QPushButton, QListWidget,
    QHBoxLayout, QLabel, QAction
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtCore import QUrl, Qt, QDir, QStandardPaths, QTimer, QThread
from PyQt5.QtGui import QIcon

# --- Definições de Caminho e Configurações ---
APP_DATA_DIR_NAME = "navegadorpytech"
PROFILES_DIR_NAME = "profiles"
DEFAULT_HOME_URL = "https://www.google.com"
DEFAULT_SEARCH_ENGINE_URL = "https://www.google.com/search?q="

def get_app_base_data_dir():
    # --- MUDANÇA AQUI: Construindo um caminho mais explícito ---
    # `os.path.expanduser('~')` retorna o diretório base do usuário (ex: C:\Users\Pedro)
    # Em seguida, adicionamos o caminho padrão para AppData\Local e o nome do seu aplicativo.
    user_home = os.path.expanduser('~')
    app_data_path = os.path.join(user_home, 'AppData', 'Local', APP_DATA_DIR_NAME)
    os.makedirs(app_data_path, exist_ok=True)
    return app_data_path
    # -----------------------------------------------------------

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

# --- CLASSE PARA EXCLUSÃO EM SEGUNDO PLANO (Ainda Mais Robusta) ---
class CleanerThread(QThread):
    def __init__(self, path_to_clean):
        super().__init__()
        self.path_to_clean = path_to_clean
        self.max_retries = 30 # Aumentado para 30 tentativas
        self.retry_delay = 1000 # 1 segundo por tentativa

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
    """
    Limpa todos os diretórios de dados de convidado de sessões anteriores
    que não foram removidos.
    """
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


class Browser(QMainWindow):
    def __init__(self, profile_name="guest_mode"):
        super().__init__()
        self.profile_name = profile_name
        self.is_guest_mode = (self.profile_name == "guest_mode")
        self.guest_temp_path = None
        self._cleaner_thread = None

        title_suffix = "Modo Convidado" if self.is_guest_mode else f"Perfil: {self.profile_name}"
        self.setWindowTitle(f"Mini Navegador PyQt - {title_suffix}")
        self.setGeometry(100, 100, 1024, 768)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        self.browser = QWebEngineView(self)
        self.web_profile = self.browser.page().profile() 

        if self.is_guest_mode:
            self.guest_temp_path = get_guest_profile_base_temp_dir()
            print(f"Iniciando em modo convidado. Dados temporários em: {self.guest_temp_path}")

            guest_cache_path = os.path.join(self.guest_temp_path, "cache")
            guest_storage_path = os.path.join(self.guest_temp_path, "storage")
            os.makedirs(guest_cache_path, exist_ok=True)
            os.makedirs(guest_storage_path, exist_ok=True)
            
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            self.web_profile.setCachePath(guest_cache_path)
            self.web_profile.setPersistentStoragePath(guest_storage_path)
            self._guest_web_profile_ref = self.web_profile 
        else:
            profile_data_path = get_profile_data_path(self.profile_name)
            self.web_profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
            self.web_profile.setCachePath(profile_data_path)
            self.web_profile.setPersistentStoragePath(profile_data_path)

        toolbar = QToolBar("Navegação")
        self.addToolBar(toolbar)

        back_button = toolbar.addAction("Voltar")
        back_button.triggered.connect(self.browser.back)

        forward_button = toolbar.addAction("Avançar")
        forward_button.triggered.connect(self.browser.forward)

        reload_button = toolbar.addAction("Recarregar")
        reload_button.triggered.connect(self.browser.reload)
        
        home_button = toolbar.addAction("Home")
        home_button.triggered.connect(self.navigate_home)

        manage_profiles_button = toolbar.addAction("Gerenciar Perfis")
        manage_profiles_button.triggered.connect(self.show_profile_management_dialog)

        self.url_bar_layout = QHBoxLayout()
        
        self.secure_icon = QLabel()
        self.secure_icon.setFixedSize(20, 20)
        self.secure_icon.setPixmap(QIcon.fromTheme("object-locked", QIcon.fromTheme("dialog-ok")).pixmap(20, 20))


        self.url_bar_layout.addWidget(self.secure_icon)
        
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar_layout.addWidget(self.url_bar)

        toolbar.addWidget(self._create_widget_from_layout(self.url_bar_layout))

        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.page().fullScreenRequested.connect(lambda request: request.accept())
        
        layout.addWidget(self.browser)

        self.browser.setUrl(QUrl(DEFAULT_HOME_URL))

    def _create_widget_from_layout(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def navigate_to_url(self):
        text = self.url_bar.text().strip()

        if not text:
            return

        if (text.startswith("http://") or
            text.startswith("https://") or
            text.startswith("ftp://") or
            ('.' in text and ' ' not in text)):
            
            if not (text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://")):
                url = "http://" + text
            else:
                url = text
            self.browser.setUrl(QUrl(url))
        else:
            search_query = QUrl.toPercentEncoding(text).data().decode('utf-8')
            search_url = DEFAULT_SEARCH_ENGINE_URL + search_query
            self.browser.setUrl(QUrl(search_url))

    def update_url_bar(self, qurl):
        self.url_bar.setText(qurl.toString())
        
        if qurl.scheme() == "https":
            self.secure_icon.setPixmap(QIcon.fromTheme("object-locked", QIcon.fromTheme("dialog-ok")).pixmap(20, 20))
            self.secure_icon.setToolTip("Conexão segura (HTTPS)")
        else:
            self.secure_icon.setPixmap(QIcon.fromTheme("dialog-warning", QIcon.fromTheme("dialog-error")).pixmap(20, 20))
            self.secure_icon.setToolTip("Conexão não segura ou HTTP")

    def navigate_home(self):
        self.browser.setUrl(QUrl(DEFAULT_HOME_URL))

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
            
            if self._guest_web_profile_ref:
                self._guest_web_profile_ref.clearHttpCache()
                self._guest_web_profile_ref.clearAllVisitedLinks()
                self._guest_web_profile_ref = None 
                print("Referências ao QWebEngineProfile do modo convidado liberadas.")

            gc.collect() 
            QTimer.singleShot(5000, lambda: self._start_cleaner_thread())
            
        super().closeEvent(event)

    def _start_cleaner_thread(self):
        """Método auxiliar para iniciar a thread de limpeza."""
        self._cleaner_thread = clean_guest_profile_data_async(self.guest_temp_path)

if __name__ == "__main__":
    clean_all_old_guest_data_on_startup()

    app = QApplication(sys.argv)

    profiles_dir = get_profiles_data_dir()
    existing_profiles = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    profiles_exist = bool(existing_profiles)

    profile_to_load = "guest_mode"

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

    browser_window = Browser(profile_to_load)
    browser_window.show()

    sys.exit(app.exec_())
