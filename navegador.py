import sys
import os
import shutil
import platform
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QTabWidget,
    QProgressBar, QDialog, QVBoxLayout, QPushButton,
    QLabel, QInputDialog, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox,
    QAction, QWidget
)
from PyQt5.QtGui import QIcon # QIcon ainda é do PyQt para ícones na UI
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSlot

# Importa o CEF
# Certifique-se de que cefpython está instalado: pip install cefpython3
from cefpython3 import cefpython as cef

# Certifique-se de que os processos CEF são executados no processo principal da GUI para evitar problemas no Linux
# Isso é uma boa prática para evitar crashes em algumas configurações
# No Linux, os processos filhos do CEF podem ter problemas se o main_loop não for executado no processo principal.
# if platform.system() == "Linux":
#     cef.WindowUtils.Set
#     cef.cef_set_global_scheme_handler_factory()
#     cef.cef_execute_process()

# Configurações globais do CEF (opcional, para depuração ou otimização)
settings = {
    "log_severity": cef.LogSeverity.INFO,
    "log_file": "debug_cef.log",
    "browser_subprocess_path": "%s/%s" % (cef.GetModuleDirectory(), "subprocess"),
    "persist_session_cookies": True, # Para manter cookies de sessão
}

class CefBrowserWidget(QWidget):
    def __init__(self, parent=None, profile_path=None):
        super().__init__(parent)
        self.browser = None
        self.profile_path = profile_path
        self.parent_window = parent # Referência à BrowserWindow para callbacks
        self.url_bar = None # Será definido pela BrowserWindow

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # Sem margens para o browser preencher o espaço

        self.original_url_sent_by_user = None # Para gerenciar a URL na barra de endereços

    def create_browser(self):
        # As configurações específicas para o profile (user_data_path)
        # devem ser passadas no momento da criação do browser.
        # cef.RequestContextSettings() permite definir o path do perfil.
        request_context_settings = {}
        if self.profile_path:
            request_context_settings["user_data_path"] = self.profile_path
            print(f"CEF Browser usando user_data_path: {self.profile_path}")

        # Cria um RequestContext com as configurações do perfil
        request_context = cef.RequestContext(request_context_settings)

        window_info = cef.WindowInfo()
        # No Linux, precisa do id da janela ou um xid
        # No Windows/macOS, pode ser o handle da janela.
        # Aqui, estamos usando a integração com PyQt.
        if platform.system() == "Windows":
            window_info.SetAsChild(self.winId())
        elif platform.system() == "Linux":
            window_info.SetAsChild(self.winId())
        elif platform.system() == "Darwin":
            window_info.SetAsOffScreen(self.winId()) # macOS precisa de offscreen rendering para embedar no PyQt5

        # Cria o navegador CEF
        self.browser = cef.CreateBrowserSync(window_info, url="https://google.com",
                                             request_context=request_context)

        # Conecta os handlers para eventos do navegador
        self.browser.SetClientHandler(LoadHandler(self.parent_window, self))
        self.browser.SetClientHandler(DisplayHandler(self.parent_window, self))
        self.browser.SetClientHandler(LifeSpanHandler(self.parent_window, self)) # Para novas janelas/abas
        
        # Redimensiona o navegador CEF quando o widget é redimensionado
        self.browser.SetBounds(0, 0, self.width(), self.height())
        self.size_timer = QTimer(self)
        self.size_timer.timeout.connect(self.on_size_timeout)
        self.size_timer.setSingleShot(True)


    def on_size_timeout(self):
        if self.browser:
            self.browser.SetBounds(0, 0, self.width(), self.height())
    
    def resizeEvent(self, event):
        # Atrasar o redimensionamento para evitar repinturas excessivas
        self.size_timer.start(100) # 100ms de atraso
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.browser:
            self.browser.CloseBrowser(True)
            self.browser = None
        super().closeEvent(event)

    def load_url(self, url):
        if self.browser:
            self.original_url_sent_by_user = url # Armazena a URL que o usuário digitou
            self.browser.LoadUrl(url)
    
    def go_back(self):
        if self.browser:
            self.browser.GoBack()

    def go_forward(self):
        if self.browser:
            self.browser.GoForward()

    def reload(self):
        if self.browser:
            self.browser.Reload()

# --- Handlers CEF (para interagir com eventos do navegador) ---

class LoadHandler(object):
    def __init__(self, main_window, browser_widget):
        self.main_window = main_window
        self.browser_widget = browser_widget

    def OnLoadStart(self, browser, frame, transition_type):
        if frame.IsMain(): # Apenas para o frame principal
            # No CEF, OnLoadStart pode ser chamado antes de OnAddressChange
            # e a URL pode não ser a URL final, mas a que iniciou o carregamento.
            # Usaremos OnAddressChange para a URL da barra.
            pass

    def OnLoadEnd(self, browser, frame, http_status_code):
        if frame.IsMain():
            # Atualiza a barra de progresso
            QApplication.instance().processEvents() # Garante que a UI responda
            self.main_window.update_progress(100, self.browser_widget)
            self.main_window.url_bar.setText(browser.GetUrl()) # Garante URL final

    def OnLoadError(self, browser, frame, error_code, error_text, failed_url):
        if frame.IsMain():
            print(f"Load Error: {error_code} - {error_text} for {failed_url}")
            # Exibe um erro na barra de URL
            self.main_window.url_bar.setText(f"Erro: {error_text} - {failed_url}")
            self.main_window.update_progress(0, self.browser_widget)


class DisplayHandler(object):
    def __init__(self, main_window, browser_widget):
        self.main_window = main_window
        self.browser_widget = browser_widget

    def OnAddressChange(self, browser, frame, url):
        # Atualiza a URL na barra de endereços apenas para a aba atual
        if self.browser_widget == self.main_window.tab_widget.currentWidget():
            self.main_window.url_bar.setText(url)
            self.main_window.url_bar.setCursorPosition(0)
            self.main_window.update_progress(0, self.browser_widget) # Reset progress for new load

    def OnTitleChange(self, browser, title):
        # Atualiza o título da aba
        if self.browser_widget == self.main_window.tab_widget.currentWidget():
            index = self.main_window.tab_widget.indexOf(self.browser_widget)
            if index != -1:
                self.main_window.tab_widget.setTabText(index, title or "Nova Aba")

    def OnLoadingProgressChange(self, browser, progress):
        # Atualiza a barra de progresso
        if self.browser_widget == self.main_window.tab_widget.currentWidget():
            self.main_window.update_progress(int(progress * 100), self.browser_widget)

class LifeSpanHandler(object):
    def __init__(self, main_window, browser_widget):
        self.main_window = main_window
        self.browser_widget = browser_widget

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name,
                      target_disposition, user_gesture, popup_features, window_info,
                      client, is_popup):
        # Lida com pop-ups e novas janelas abrindo em novas abas
        print(f"OnBeforePopup: {target_url}")
        self.main_window.add_new_tab(QUrl(target_url))
        return True # Retorna True para cancelar a criação da nova janela pelo CEF


# --- Classe Principal da Janela ---

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Navegador PyTech 3 (CEFPython)")
        self.setGeometry(100, 100, 1024, 768)

        self.data_dir = os.path.join(os.path.expanduser('~'), '.navegadorpytech3_cef_data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.profiles_file = os.path.join(self.data_dir, 'profiles.txt')

        self.profiles = self.load_profiles()
        self.current_profile_name = "default"
        self.active_profile_path = None # Caminho completo do perfil CEF

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.current_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.setTabsClosable(True)

        self.create_toolbar()

        self.add_profile_if_none_exists()
        self.open_profile_selector()

        # Inicia o timer CEF para processar eventos
        self.cef_timer = QTimer(self)
        self.cef_timer.timeout.connect(self.cef_message_loop)
        self.cef_timer.start(10) # 10ms é um bom intervalo para o message loop


    def cef_message_loop(self):
        cef.MessageLoopWork() # Necessário para o CEF funcionar corretamente

    def create_toolbar(self):
        toolbar = QToolBar("Navegação")
        self.addToolBar(toolbar)

        back_button = QAction(QIcon.fromTheme("go-previous"), "<- Voltar", self)
        back_button.triggered.connect(self.go_back)
        toolbar.addAction(back_button)

        forward_button = QAction(QIcon.fromTheme("go-next"), "Avançar ->", self)
        forward_button.triggered.connect(self.go_forward)
        toolbar.addAction(forward_button)

        reload_button = QAction(QIcon.fromTheme("view-refresh"), "Recarregar", self)
        reload_button.triggered.connect(self.reload)
        toolbar.addAction(reload_button)

        home_button = QAction(QIcon.fromTheme("go-home"), "Home", self)
        home_button.triggered.connect(self.navigate_home)
        toolbar.addAction(home_button)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.url_bar)

        new_tab_button = QAction(QIcon.fromTheme("tab-new"), "+ Nova Aba", self)
        new_tab_button.triggered.connect(self.add_new_tab)
        toolbar.addAction(new_tab_button)

        profile_button = QAction(QIcon.fromTheme("system-users"), "Perfis", self)
        profile_button.triggered.connect(self.open_profile_selector)
        toolbar.addAction(profile_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)

    @pyqtSlot(QUrl, str)
    @pyqtSlot(str, str)
    def add_new_tab(self, qurl=None, label="Nova Aba", profile_path=None):
        if self.active_profile_path is None:
            QMessageBox.critical(self, "Erro de Perfil", "Nenhum perfil selecionado. Por favor, selecione ou crie um perfil.")
            return

        # Passa o caminho do perfil para o widget do navegador CEF
        browser_widget = CefBrowserWidget(self, profile_path=self.active_profile_path)
        browser_widget.url_bar = self.url_bar # Passa a referência da url_bar

        i = self.tab_widget.addTab(browser_widget, label)
        self.tab_widget.setCurrentIndex(i)

        browser_widget.create_browser() # Cria o navegador CEF dentro do widget

        # Define a URL inicial
        if qurl is None:
            browser_widget.load_url('https://google.com')
            self.url_bar.setText('https://google.com')
        else:
            browser_widget.load_url(qurl.toString() if isinstance(qurl, QUrl) else qurl)
            self.url_bar.setText(qurl.toString() if isinstance(qurl, QUrl) else qurl)
        
        # Conecta o sinal urlChanged que será emitido pelo LoadHandler
        # (Isso é feito via o handler no CEF, não diretamente no QWebEngineView)

    def navigate_home(self):
        current_browser = self.tab_widget.currentWidget()
        if current_browser and isinstance(current_browser, CefBrowserWidget):
            current_browser.load_url('https://google.com')

    def navigate_to_url(self):
        current_browser = self.tab_widget.currentWidget()
        if current_browser and isinstance(current_browser, CefBrowserWidget):
            url_text = self.url_bar.text()
            if not url_text.startswith(('http://', 'https://')):
                url_text = 'http://' + url_text # Adiciona esquema padrão
            current_browser.load_url(url_text)

    def update_urlbar(self, url, browser_widget=None):
        if browser_widget == self.tab_widget.currentWidget():
            self.url_bar.setText(url)
            self.url_bar.setCursorPosition(0)

    def update_progress(self, progress, browser_widget=None):
        if browser_widget == self.tab_widget.currentWidget():
            if progress == 100:
                self.progress_bar.setVisible(False)
            else:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(progress)

    def current_tab_changed(self, index):
        if index != -1:
            browser_widget = self.tab_widget.widget(index)
            if browser_widget and isinstance(browser_widget, CefBrowserWidget) and browser_widget.browser:
                # Obtém a URL atual do browser CEF e atualiza a barra
                self.url_bar.setText(browser_widget.browser.GetUrl())
                self.url_bar.setCursorPosition(0)
                self.update_progress(0, browser_widget) # Reseta a barra ao mudar de aba

    def close_current_tab(self, index):
        if self.tab_widget.count() < 2:
            self.close()
        else:
            browser_widget_to_close = self.tab_widget.widget(index)
            if browser_widget_to_close and isinstance(browser_widget_to_close, CefBrowserWidget):
                browser_widget_to_close.closeEvent(None) # Garante que o CEF seja fechado corretamente
            self.tab_widget.removeTab(index)

    def go_back(self):
        current_browser = self.tab_widget.currentWidget()
        if current_browser and isinstance(current_browser, CefBrowserWidget):
            current_browser.go_back()

    def go_forward(self):
        current_browser = self.tab_widget.currentWidget()
        if current_browser and isinstance(current_browser, CefBrowserWidget):
            current_browser.go_forward()

    def reload(self):
        current_browser = self.tab_widget.currentWidget()
        if current_browser and isinstance(current_browser, CefBrowserWidget):
            current_browser.reload()

    # --- Funções de gerenciamento de perfis ---

    def load_profiles(self):
        profiles = {}
        if os.path.exists(self.profiles_file):
            with open(self.profiles_file, 'r') as f:
                for line in f:
                    name = line.strip()
                    if name:
                        profiles[name] = True
        return profiles

    def save_profiles(self):
        with open(self.profiles_file, 'w') as f:
            for name in self.profiles.keys():
                f.write(name + '\n')

    def select_profile(self, profile_name):
        self.current_profile_name = profile_name
        self.active_profile_path = os.path.join(self.data_dir, profile_name)
        os.makedirs(self.active_profile_path, exist_ok=True)
        print(f"Perfil '{self.current_profile_name}' selecionado. Dados em: {self.active_profile_path}")
        self.setWindowTitle(f"Navegador PyTech 3 (CEFPython) - Perfil: {self.current_profile_name}")

        # Recria as abas com o novo perfil
        self.tab_widget.clear()
        self.add_new_tab(label=f"Página Inicial ({profile_name})", profile_path=self.active_profile_path)

        # Atualiza o estado da lista de perfis no diálogo (se estiver aberto)
        if 'profile_list_dialog' in globals() and profile_list_dialog.isVisible():
            for i in range(profile_list_dialog.profile_list_widget.count()):
                item = profile_list_dialog.profile_list_widget.item(i)
                if item.text() == profile_name:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)


    def open_profile_selector(self):
        global profile_list_dialog
        profile_list_dialog = QDialog(self)
        profile_list_dialog.setWindowTitle("Gerenciar Perfis")
        layout = QVBoxLayout()

        profile_list_dialog.profile_list_widget = QListWidget()
        for p_name in self.profiles.keys():
            item = QListWidgetItem(p_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if p_name == self.current_profile_name:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            profile_list_dialog.profile_list_widget.addItem(item)
        
        profile_list_dialog.profile_list_widget.itemClicked.connect(lambda item: self.select_profile(item.text()))

        layout.addWidget(profile_list_dialog.profile_list_widget)

        add_button = QPushButton("Adicionar Perfil")
        add_button.clicked.connect(lambda: self.add_profile(profile_list_dialog.profile_list_widget))
        
        delete_button = QPushButton("Excluir Perfil Selecionado")
        delete_button.clicked.connect(lambda: self.delete_profile(profile_list_dialog.profile_list_widget))

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(profile_list_dialog.accept)

        dialog_buttons_layout = QHBoxLayout()
        dialog_buttons_layout.addWidget(add_button)
        dialog_buttons_layout.addWidget(delete_button)
        layout.addLayout(dialog_buttons_layout)
        layout.addWidget(close_button)

        profile_list_dialog.setLayout(layout)
        profile_list_dialog.exec()

    def add_profile(self, profile_list_widget):
        new_profile_name, ok = QInputDialog.getText(self, "Novo Perfil", "Nome do novo perfil:")
        if ok and new_profile_name:
            if new_profile_name in self.profiles:
                QMessageBox.warning(self, "Nome Inválido", "Um perfil com este nome já existe.")
            else:
                self.profiles[new_profile_name] = True
                self.save_profiles()
                item = QListWidgetItem(new_profile_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                profile_list_widget.addItem(item)
                self.select_profile(new_profile_name)

    def delete_profile(self, profile_list_widget):
        selected_items = profile_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nenhum Perfil Selecionado", "Por favor, selecione um perfil para excluir.")
            return

        reply = QMessageBox.question(self, 'Confirmar Exclusão', 
                                     "Tem certeza que deseja excluir o perfil selecionado?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                profile_name = item.text()
                if profile_name == self.current_profile_name:
                    QMessageBox.critical(self, "Erro", "Não é possível excluir o perfil atualmente em uso.")
                    return

                del self.profiles[profile_name]
                self.save_profiles()
                
                profile_path = os.path.join(self.data_dir, profile_name)
                if os.path.exists(profile_path):
                    try:
                        shutil.rmtree(profile_path)
                        print(f"Diretório do perfil '{pr
