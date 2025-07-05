import sys
import os
import json
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QLineEdit, QPushButton, QAction, QMenu, QDialog, QLabel,
    QCheckBox, QMessageBox, QInputDialog
)
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon

# Certifique-se de que cefpython está disponível (instale com pip install cefpython3)
try:
    from cefpython3 import cefpython as cef
except ImportError:
    print("Erro: A biblioteca 'cefpython3' não foi encontrada.")
    print("Por favor, instale-a usando: pip install cefpython3")
    sys.exit(1)

# --- Configurações do Navegador ---
APP_NAME = "NavegadorPyTech"
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME.lower())
PROFILES_DIR = os.path.join(APP_DATA_DIR, "profiles")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")
DEFAULT_HOMEPAGE = "https://www.google.com"

# Garante que os diretórios necessários existem
os.makedirs(PROFILES_DIR, exist_ok=True)


class BrowserWidget(QWidget):
    """Widget que encapsula o navegador CEF."""
    def __init__(self, parent=None, profile_path=None):
        super().__init__(parent)
        self.browser = None
        self.profile_path = profile_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        window_info = cef.WindowInfo()
        rect = [0, 0, self.width(), self.height()]
        window_info.SetAsChild(self.winId(), rect)

        settings = {
            "window_info": window_info,
            "url": DEFAULT_HOMEPAGE,
        }

        # Configura o diretório de dados do usuário para o perfil
        if self.profile_path:
            settings["user_data_path"] = self.profile_path
            print(f"DEBUG: Carregando perfil de dados do usuário: {self.profile_path}")
        else:
            # Modo convidado não salva dados, usa um diretório temporário ou omite para usar o padrão CEF
            # Para garantir que não salva nada, podemos usar um diretório temporário ou deixar o CEF gerenciar
            # mas o CEF pode criar um diretório padrão. Melhor não passar user_data_path para modo convidado.
            print("DEBUG: Modo convidado ativado, não salvando dados.")

        self.browser = cef.CreateBrowserSync(**settings)
        layout.addWidget(self) # Adiciona o próprio widget ao layout para que o CEF possa renderizar nele

    def resizeEvent(self, event):
        if self.browser:
            self.browser.SetBounds(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.browser:
            self.browser.CloseBrowser(True)
            self.browser = None # Libera a referência para o navegador
        super().closeEvent(event)

class ProfileManager:
    """Gerencia a criação, seleção e remoção de perfis."""
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {"default_profile": None, "profiles": []}

    def _save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_profiles(self):
        return self.config["profiles"]

    def get_default_profile(self):
        return self.config["default_profile"]

    def set_default_profile(self, profile_name):
        self.config["default_profile"] = profile_name
        self._save_config()

    def add_profile(self, profile_name, is_default=False):
        if profile_name not in self.config["profiles"]:
            self.config["profiles"].append(profile_name)
            # Cria o diretório para o novo perfil
            profile_path = os.path.join(PROFILES_DIR, profile_name)
            os.makedirs(profile_path, exist_ok=True)
            print(f"Perfil '{profile_name}' criado em: {profile_path}")

            if is_default:
                self.set_default_profile(profile_name)
            self._save_config()
            return True
        return False # Perfil já existe

    def remove_profile(self, profile_name):
        if profile_name in self.config["profiles"]:
            self.config["profiles"].remove(profile_name)
            if self.config["default_profile"] == profile_name:
                self.config["default_profile"] = None
            
            # Remove o diretório do perfil
            profile_path = os.path.join(PROFILES_DIR, profile_name)
            if os.path.exists(profile_path):
                shutil.rmtree(profile_path)
                print(f"Diretório do perfil '{profile_name}' removido: {profile_path}")

            self._save_config()
            return True
        return False

class CreateProfileDialog(QDialog):
    """Diálogo para criar um novo perfil."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Criar Novo Perfil")
        self.setGeometry(200, 200, 300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.name_label = QLabel("Nome do Perfil:")
        layout.addWidget(self.name_label)

        self.name_input = QLineEdit(self)
        layout.addWidget(self.name_input)

        self.default_checkbox = QCheckBox("Definir como padrão ao iniciar", self)
        layout.addWidget(self.default_checkbox)

        self.create_button = QPushButton("Criar Perfil", self)
        self.create_button.clicked.connect(self.accept)
        layout.addWidget(self.create_button)

        self.setLayout(layout)

    def get_profile_data(self):
        return self.name_input.text(), self.default_checkbox.isChecked()


class MainWindow(QMainWindow):
    """Janela principal do Navegador PyTech."""
    def __init__(self):
        super().__init__()
        self.profile_manager = ProfileManager()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1024, 768)
        self.setWindowIcon(QIcon.fromTheme("web-browser")) # Tenta usar um ícone de navegador do sistema

        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setTabsClosable(True)
        self.central_widget.tabCloseRequested.connect(self.close_tab)

        self.init_menu()
        self.show_startup_dialog()

    def init_menu(self):
        # Menu Arquivo
        file_menu = self.menuBar().addMenu("&Arquivo")
        
        new_tab_action = QAction("Nova Aba", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.add_new_tab)
        file_menu.addAction(new_tab_action)

        exit_action = QAction("&Sair", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Menu Perfis
        profiles_menu = self.menuBar().addMenu("&Perfis")

        create_profile_action = QAction("Criar Novo Perfil...", self)
        create_profile_action.triggered.connect(self.show_create_profile_dialog)
        profiles_menu.addAction(create_profile_action)

        manage_profiles_action = QAction("Gerenciar Perfis...", self)
        manage_profiles_action.triggered.connect(self.show_manage_profiles_dialog)
        profiles_menu.addAction(manage_profiles_action)

        profiles_menu.addSeparator()
        self.profile_actions_menu = QMenu("Selecionar Perfil", self)
        profiles_menu.addMenu(self.profile_actions_menu)
        self.update_profile_menu() # Popula o menu de seleção de perfis

    def update_profile_menu(self):
        self.profile_actions_menu.clear()
        profiles = self.profile_manager.get_profiles()
        if not profiles:
            no_profiles_action = QAction("Nenhum perfil encontrado", self)
            no_profiles_action.setEnabled(False)
            self.profile_actions_menu.addAction(no_profiles_action)
            return

        for profile_name in profiles:
            action = QAction(profile_name, self)
            action.triggered.connect(lambda checked, name=profile_name: self.switch_to_profile(name))
            self.profile_actions_menu.addAction(action)

    def switch_to_profile(self, profile_name):
        reply = QMessageBox.question(
            self, 'Trocar Perfil',
            f"Você quer fechar todas as abas e iniciar uma nova sessão com o perfil '{profile_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_all_tabs()
            profile_path = os.path.join(PROFILES_DIR, profile_name)
            self.add_new_tab(profile_path=profile_path, tab_title=profile_name)

    def show_startup_dialog(self):
        """Mostra o pop-up de seleção de perfil ao iniciar."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Bem-vindo ao Navegador PyTech")
        msg_box.setText("Selecione um perfil para iniciar:")

        guest_button = msg_box.addButton("Modo Convidado", QMessageBox.ActionRole)
        
        profiles = self.profile_manager.get_profiles()
        profile_buttons = []
        for profile_name in profiles:
            button = msg_box.addButton(profile_name, QMessageBox.ActionRole)
            profile_buttons.append((profile_name, button))

        # Adiciona a opção de perfil padrão, se houver
        default_profile = self.profile_manager.get_default_profile()
        if default_profile and default_profile in profiles:
            msg_box.setDefaultButton(next(btn for name, btn in profile_buttons if name == default_profile))
            
        msg_box.exec_()

        clicked_button = msg_box.clickedButton()

        if clicked_button == guest_button:
            self.add_new_tab(profile_path=None, tab_title="Convidado")
        else:
            for profile_name, button in profile_buttons:
                if clicked_button == button:
                    profile_path = os.path.join(PROFILES_DIR, profile_name)
                    self.add_new_tab(profile_path=profile_path, tab_title=profile_name)
                    break
            else: # Se nenhuma opção foi selecionada ou se a janela foi fechada sem escolher
                 # Ou se não houver perfis e o modo convidado não for clicado
                self.add_new_tab(profile_path=None, tab_title="Convidado")


    def add_new_tab(self, url=DEFAULT_HOMEPAGE, profile_path=None, tab_title="Nova Aba"):
        browser_widget = BrowserWidget(self, profile_path=profile_path)
        index = self.central_widget.addTab(browser_widget, tab_title)
        self.central_widget.setCurrentIndex(index)
        browser_widget.browser.LoadUrl(url)

    def close_tab(self, index):
        widget = self.central_widget.widget(index)
        if widget:
            widget.closeEvent(None) # Chama o closeEvent do BrowserWidget para liberar o CEF
            self.central_widget.removeTab(index)

    def clear_all_tabs(self):
        while self.central_widget.count() > 0:
            self.close_tab(0)

    def show_create_profile_dialog(self):
        dialog = CreateProfileDialog(self)
        if dialog.exec_():
            profile_name, is_default = dialog.get_profile_data()
            if not profile_name:
                QMessageBox.warning(self, "Erro", "O nome do perfil não pode ser vazio.")
                return

            if self.profile_manager.add_profile(profile_name, is_default):
                QMessageBox.information(self, "Sucesso", f"Perfil '{profile_name}' criado com sucesso!")
                self.update_profile_menu()
            else:
                QMessageBox.warning(self, "Erro", f"O perfil '{profile_name}' já existe.")

    def show_manage_profiles_dialog(self):
        profiles = self.profile_manager.get_profiles()
        if not profiles:
            QMessageBox.information(self, "Gerenciar Perfis", "Nenhum perfil para gerenciar.")
            return

        items = profiles
        item, ok = QInputDialog.getItem(
            self, "Gerenciar Perfis", "Selecione um perfil para remover:",
            items, 0, False
        )
        if ok and item:
            reply = QMessageBox.question(
                self, 'Remover Perfil',
                f"Você tem certeza que deseja remover o perfil '{item}'? Todos os dados serão perdidos.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.profile_manager.remove_profile(item):
                    QMessageBox.information(self, "Sucesso", f"Perfil '{item}' removido com sucesso!")
                    self.update_profile_menu()
                    # Se o perfil removido era o atual, voltar para modo convidado
                    if self.central_widget.count() > 0:
                        current_browser_widget = self.central_widget.currentWidget()
                        # Verifica se o caminho do perfil atual termina com o nome do perfil removido
                        if current_browser_widget and current_browser_widget.profile_path and current_browser_widget.profile_path.endswith(os.sep + item):
                            self.clear_all_tabs()
                            self.add_new_tab(profile_path=None, tab_title="Convidado")
                else:
                    QMessageBox.warning(self, "Erro", f"Não foi possível remover o perfil '{item}'.")

def main():
    # Inicializa CEF Python
    sys.excepthook = cef.ExceptHook  # Para lidar com exceções não capturadas
    cef.Initialize()

    app = QApplication(sys.argv)
    
    # Adiciona um estilo visual (opcional)
    # app.setStyle("Fusion") 

    main_window = MainWindow()
    main_window.show()

    # Loop de eventos do CEF
    cef.MessageLoop()

    # Finaliza CEF Python
    cef.Shutdown()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
