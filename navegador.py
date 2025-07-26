import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QWidget,
    QVBoxLayout, QMessageBox, QInputDialog, QDialog, QPushButton, QListWidget,
    QHBoxLayout, QAction, QLabel
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QDir, QStandardPaths
from PyQt5.QtGui import QIcon

# --- Definições de Caminho ---
APP_DATA_DIR_NAME = "navegadorpytech"
PROFILES_DIR_NAME = "profiles"
DEFAULT_HOME_URL = "https://www.google.com"
DEFAULT_SEARCH_ENGINE_URL = "https://www.google.com/search?q="

def get_app_base_data_dir():
    """
    Retorna o diretório base para os dados da aplicação.
    Ex: ~/.local/share/navegadorpytech/
    """
    return os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
        APP_DATA_DIR_NAME
    )

def get_profiles_data_dir():
    """
    Retorna o diretório onde os perfis persistentes são armazenados.
    Ex: ~/.local/share/navegadorpytech/profiles/
    """
    profiles_path = os.path.join(get_app_base_data_dir(), PROFILES_DIR_NAME)
    os.makedirs(profiles_path, exist_ok=True)
    return profiles_path

def get_profile_data_path(profile_name):
    """
    Retorna o caminho completo para o diretório de dados de um perfil persistente.
    Cria o diretório se ele não existir.
    """
    profile_data_path = os.path.join(get_profiles_data_dir(), profile_name)
    os.makedirs(profile_data_path, exist_ok=True)
    return profile_data_path

def get_guest_profile_data_path():
    """
    Retorna um caminho temporário para o modo convidado.
    """
    temp_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation),
                            f"{APP_DATA_DIR_NAME}_guest_temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def clean_guest_profile_data(path):
    """
    Remove o diretório de dados do perfil convidado.
    """
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"Dados do modo convidado apagados de: {path}")
        except OSError as e:
            print(f"Erro ao apagar dados do modo convidado em {path}: {e}")

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

        title_suffix = "Modo Convidado" if self.is_guest_mode else f"Perfil: {self.profile_name}"
        self.setWindowTitle(f"Mini Navegador PyQt - {title_suffix}")
        self.setGeometry(100, 100, 1024, 768)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        self.browser = QWebEngineView(self)
        self.web_profile = self.browser.page().profile()

        if self.is_guest_mode:
            self.guest_temp_path = get_guest_profile_data_path()
            print(f"Iniciando em modo convidado. Dados temporários em: {self.guest_temp_path}")
            self.web_profile.setPersistentCookiesPolicy(self.web_profile.NoPersistentCookies) 
            self.web_profile.setCachePath(self.guest_temp_path)
            self.web_profile.setPersistentStoragePath(self.guest_temp_path)
        else:
            profile_data_path = get_profile_data_path(self.profile_name)
            self.web_profile.setPersistentCookiesPolicy(self.web_profile.AllowPersistentCookies)
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
        # Tenta carregar ícones do tema, com fallback para ícones padrão (se existirem)
        # Note: Para QIcon(":/icons/locked.png") funcionar, você precisaria de um arquivo .qrc
        # Por enquanto, confiamos mais no fromTheme ou na ausência de ícone se o tema falhar.
        self.secure_icon.setPixmap(QIcon.fromTheme("object-locked", QIcon.fromTheme("dialog-ok")).pixmap(20, 20))


        self.url_bar_layout.addWidget(self.secure_icon)
        
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar_layout.addWidget(self.url_bar)

        toolbar.addWidget(self._create_widget_from_layout(self.url_bar_layout))

        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.page().fullScreenRequested.connect(lambda request: request.accept())
        
        # REMOVIDA A LINHA self.browser.page().certificateError.connect(self.handle_certificate_error)
        # pois está causando o AttributeError
        
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

    # O método handle_certificate_error foi removido, pois o sinal não pôde ser conectado.
    # Se você precisar muito dessa funcionalidade, precisaremos investigar a API exata para a sua versão do PyQtWebEngine.

    def closeEvent(self, event):
        if self.is_guest_mode and self.guest_temp_path:
            clean_guest_profile_data(self.guest_temp_path)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    profiles_dir_exists = os.path.exists(get_profiles_data_dir()) and len(os.listdir(get_profiles_data_dir())) > 0

    profile_to_load = "guest_mode"

    if profiles_dir_exists:
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
