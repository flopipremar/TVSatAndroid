from kivy.app import App
from kivy.lang import Builder
import os
from informeviewer import InformeViewer
from kivy.uix.screenmanager import ScreenManager, Screen # Importa Screen
from db import crear_tablas
from clientesscreen import ClientesScreen
from usuariosscreen import UsuariosScreen
from creditosscreen import CreditosScreen
from informesscreen import InformesScreen
from migradorscreen import MigradorScreen
from renovacionesscreen import RenovacionesScreen

# Necesitamos definir la clase del menú aquí o en un archivo aparte
class MenuScreen(Screen):
    pass

class MainApp(App):
    def build(self):
        crear_tablas()

        # 1. Cargamos todos los archivos .kv para que Kivy conozca las "reglas"
       base_dir = os.path.dirname(os.path.abspath(__file__))
       Builder.load_file(os.path.join(base_dir, "menu.kv"))
       Builder.load_file(os.path.join(base_dir, "clientes.kv"))
       Builder.load_file(os.path.join(base_dir, "usuarios.kv"))
       Builder.load_file(os.path.join(base_dir, "creditos.kv"))
       Builder.load_file(os.path.join(base_dir, "informes.kv"))
       Builder.load_file(os.path.join(base_dir, "migrador.kv"))
       Builder.load_file(os.path.join(base_dir, "renovaciones.kv"))
       Builder.load_file(os.path.join(base_dir, "informeviewer.kv"))

        sm = ScreenManager()

        # 2. Agregamos las INSTANCIAS de las pantallas al Manager
        # Asegúrate de que en tus archivos .kv los nombres coincidan (MenuScreen, ClientesScreen, etc.)
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(ClientesScreen(name="clientes"))
        sm.add_widget(UsuariosScreen(name="usuarios"))
        sm.add_widget(CreditosScreen(name="creditos"))
        sm.add_widget(InformesScreen(name="informes"))
        sm.add_widget(MigradorScreen(name='migrador'))
        sm.add_widget(RenovacionesScreen(name="renovaciones"))
        sm.add_widget(InformeViewer())

        return sm

if __name__ == "__main__":
    MainApp().run()
