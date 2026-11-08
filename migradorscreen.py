from db import get_conn
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.metrics import dp

class MigradorScreen(Screen):
    clientes_impakto = ListProperty([])
    entradas_migracion = []
    clientes_impakto_full = []
    usuarios = ListProperty([])
    usuarios_full = []

    def on_pre_enter(self):
        self.cargar_usuarios()
        self.cargar_clientes_impakto()
        self.ids.contenedor_migracion.clear_widgets()

    def cargar_usuarios(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT usuario
            FROM usuarios
            WHERE sistema = 'Impakto'
            AND activo = 1
            ORDER BY usuario
        """)

        filas = cur.fetchall()
        conn.close()

        self.usuarios_full = [fila[0] for fila in filas]
        self.usuarios = self.usuarios_full.copy()

    def filtrar_usuarios(self, texto):
        texto = texto.strip().lower()

        if texto == "":
            self.usuarios = self.usuarios_full.copy()
        else:
            self.usuarios = [
                u for u in self.usuarios_full
                if texto in u.lower()
            ]

        self.ids.usuario_spinner.values = self.usuarios
    
    def buscar_por_usuario(self, usuario):
        self.ids.contenedor_migracion.clear_widgets()
        self.entradas_migracion = []

        if usuario == "Seleccionar usuario":
            return

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                u.id,
                c.nombre,
                u.ident_disp
            FROM usuarios u
            JOIN clientes c
                ON c.id = u.cliente_id
            WHERE u.usuario = ?
            AND u.sistema = 'Impakto'
            AND u.activo = 1
            ORDER BY c.nombre
        """, (usuario,))

        cuentas = cur.fetchall()
        conn.close()

        for id_reg, nombre_cliente, id_disp in cuentas:
            fila = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))

            fila.add_widget(
                Label(
                    text=nombre_cliente,
                    size_hint_x=0.45
                )
            )

            ent = TextInput(
                text=str(id_disp if id_disp else ""),
                hint_text="ID Dispositivo",
                multiline=False
            )

            fila.add_widget(ent)

            self.ids.contenedor_migracion.add_widget(fila)

            self.entradas_migracion.append({
                'id_registro': id_reg,
                'input': ent
            })

    def cargar_clientes_impakto(self):
        conn = get_conn(); cur = conn.cursor()
        # Filtramos solo clientes de Impakto activos
        cur.execute("""
            SELECT DISTINCT c.id, c.nombre 
            FROM clientes c
            JOIN usuarios u ON c.id = u.cliente_id
            WHERE u.sistema = 'Impakto' AND c.activo = 1
            ORDER BY c.nombre
        """)
        filas = cur.fetchall(); conn.close()
        self.clientes_impakto_full = [f"{f[0]} - {f[1]}" for f in filas]
        self.clientes_impakto = self.clientes_impakto_full.copy()

    def filtrar_clientes(self, texto):
        texto = texto.strip().lower()

        if texto == "":
            self.clientes_impakto = self.clientes_impakto_full.copy()
        else:
            self.clientes_impakto = [
                c for c in self.clientes_impakto_full
                if texto in c.lower()
            ]

        self.ids.cliente_spinner.values = self.clientes_impakto
        
    def generar_filas_migracion(self, texto_spinner):
        self.ids.contenedor_migracion.clear_widgets()
        self.entradas_migracion = []
        if " - " not in texto_spinner: return

        cliente_id = int(texto_spinner.split(" - ")[0])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT id, usuario, ident_disp FROM usuarios WHERE cliente_id = ? AND sistema = 'Impakto'", (cliente_id,))
        cuentas = cur.fetchall(); conn.close()

        for id_reg, usu, id_disp in cuentas:
            fila = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
            fila.add_widget(Label(text=f"Cuenta: {usu}", size_hint_x=0.4))
            
            ent = TextInput(text=str(id_disp if id_disp else ""), hint_text="ID Dispositivo", multiline=False)
            fila.add_widget(ent)
            
            self.ids.contenedor_migracion.add_widget(fila)
            self.entradas_migracion.append({'id_registro': id_reg, 'input': ent})

    def limpiar_pantalla(self):
        self.ids.filtro_cliente.text = ""
        self.ids.filtro_usuario.text = ""

        self.ids.cliente_spinner.text = "Seleccionar"
        self.ids.usuario_spinner.text = "Seleccionar"

        self.ids.cliente_spinner.values = self.clientes_impakto_full.copy()
        self.ids.usuario_spinner.values = self.usuarios_full.copy()

        self.ids.contenedor_migracion.clear_widgets()
        self.entradas_migracion = []
    
    def guardar_migracion(self):
        if not self.entradas_migracion: return
        conn = get_conn(); cur = conn.cursor()
        try:
            for item in self.entradas_migracion:
                nuevo_id = item['input'].text.strip()
                cur.execute("UPDATE usuarios SET ident_disp = ? WHERE id = ?", (nuevo_id, item['id_registro']))
            conn.commit()
            self.manager.get_screen('usuarios').popup("Éxito", "IDs actualizados correctamente")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()