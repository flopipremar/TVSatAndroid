from db import get_conn
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from datetime import datetime

class UsuariosScreen(Screen):
    clientes = ListProperty([]) # Esta es la lista filtrada que ve el Spinner
    clientes_full = []          # Aquí guardamos la lista completa original
    entradas_dinamicas = []

    def on_pre_enter(self):
        self.cargar_clientes()
        self.limpiar_pantalla()

    def buscar(self, texto):

        texto = texto.strip().lower()

        if texto == "":
            self.clientes = self.clientes_full.copy()
            self.ids.cliente_spinner.values = self.clientes
            self.ids.cliente_spinner.text = "Seleccionar cliente"
            self.ids.contenedor_usuarios.clear_widgets()
            return

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT
                c.id,
                c.nombre
            FROM clientes c
            LEFT JOIN usuarios u
                ON u.cliente_id = c.id
            WHERE
                LOWER(c.nombre) LIKE ?
                OR LOWER(IFNULL(u.usuario,'')) LIKE ?
                OR LOWER(IFNULL(c.telefono,'')) LIKE ?
            ORDER BY c.nombre
        """, (
            f"%{texto}%",
            f"%{texto}%",
            f"%{texto}%"
        ))

        filas = cur.fetchall()

        conn.close()

        if not filas:
            self.clientes = []
            self.ids.cliente_spinner.values = []
            self.ids.cliente_spinner.text = "Sin resultados"
            self.ids.contenedor_usuarios.clear_widgets()
            return

        self.clientes = [f"{f[0]} - {f[1]}" for f in filas]
        self.ids.cliente_spinner.values = self.clientes

        if len(filas) == 1:
            cliente = f"{filas[0][0]} - {filas[0][1]}"
            self.ids.cliente_spinner.text = cliente
            self.generar_filas_usuarios(cliente)

    def cargar_clientes(self):
        """Carga la lista original de clientes"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nombre
            FROM clientes
            WHERE activo = 1
            ORDER BY nombre
        """)

        filas = cur.fetchall()
        conn.close()

        self.clientes_full = [f"{f[0]} - {f[1]}" for f in filas]

        # IMPORTANTE: crear una copia
        self.clientes = self.clientes_full.copy()

    def filtrar_clientes(self, texto):
        """ Filtra el Spinner de clientes según lo que escribís en el TextInput """
        t = texto.lower()
        if not t:
            self.clientes = self.clientes_full
        else:
            self.clientes = [c for c in self.clientes_full if t in c.lower()]
        
        # Opcional: Abre el spinner automáticamente al filtrar (si el KV lo permite)
        if self.clientes:
            self.ids.cliente_spinner.is_open = True
    
    def generar_filas_usuarios(self, texto_spinner):
        """ Crea los campos según lo que haya en la DB para ese cliente """
        self.ids.contenedor_usuarios.clear_widgets()
        self.entradas_dinamicas.clear() 
        if " - " not in texto_spinner: return
        try:
            cliente_id = int(texto_spinner.split(" - ")[0])
            conn = get_conn(); cur = conn.cursor()
            cur.execute("SELECT id, sistema, usuario, fecha_vencimiento FROM usuarios WHERE cliente_id = ?", (cliente_id,))
            existentes = cur.fetchall(); conn.close()
            for f in existentes: self.agregar_fila_interfaz(f[0], f[1], f[2], f[3])
        except: pass

    def agregar_fila_interfaz(self, db_id, sistema, usuario, vencimiento):
        """ Crea la fila visual y guarda la referencia en la lista """
        fila = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        sis = Spinner(text=sistema, values=["ItvOpen", "Impakto", "IPTV", "IKS81W"], size_hint_x=0.3)
        usu = TextInput(text=usuario, multiline=False)
        ven = TextInput(text=vencimiento, multiline=False, size_hint_x=0.3)
        btn_del = Button(text="X", size_hint_x=None, width=dp(40), background_color=(1, 0.3, 0.3, 1))
        btn_del.bind(on_release=lambda x: self.eliminar_usuario_db(db_id))
        
        for w in [sis, usu, ven, btn_del]: fila.add_widget(w)
        self.ids.contenedor_usuarios.add_widget(fila)
        self.entradas_dinamicas.append({'id': db_id, 'sistema': sis, 'usuario': usu, 'venc': ven})

    def nueva_fila_vacia(self):
        """ Botón '+' para agregar un dispositivo extra """
        if " - " not in self.ids.cliente_spinner.text:
            self.popup("Error", "Seleccioná un cliente"); return
        self.agregar_fila_interfaz(None, "ItvOpen", "", datetime.now().strftime("%d/%m/%Y"))

    def guardar_usuario(self):
        """ Guarda todos los usuarios del cliente validando límites """
        if " - " not in self.ids.cliente_spinner.text: return
        try:
            cliente_id = int(self.ids.cliente_spinner.text.split(" - ")[0])
            conteo = {}
            # Validación de reglas de negocio
            for ent in self.entradas_dinamicas:
                u, s = ent['usuario'].text.strip().lower(), ent['sistema'].text
                if u:
                    llave = f"{s}_{u}"
                    conteo[llave] = conteo.get(llave, 0) + 1
                    if (s == "ItvOpen" and conteo[llave] > 1) or (s in ["Impakto", "IPTV"] and conteo[llave] > 3):
                        self.popup("Límite Excedido", f"El usuario '{u}' supera el máximo en {s}"); return

            conn = get_conn(); cur = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE cliente_id = ?", (cliente_id,))
            for ent in self.entradas_dinamicas:
                u = ent['usuario'].text.strip()
                if u: cur.execute("INSERT INTO usuarios (cliente_id, sistema, usuario, fecha_vencimiento, activo) VALUES (?,?,?,?,1)", 
                                (cliente_id, ent['sistema'].text, u, ent['venc'].text.strip()))
            conn.commit(); conn.close()
            self.popup("Éxito", "Cuentas actualizadas"); self.generar_filas_usuarios(self.ids.cliente_spinner.text)
        except Exception as e: self.popup("Error", str(e))

    def eliminar_usuario_db(self, u_id):
        if u_id:
            conn = get_conn(); cur = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE id = ?", (u_id,))
            conn.commit(); conn.close()
            self.generar_filas_usuarios(self.ids.cliente_spinner.text)
            self.popup("OK", "Eliminado de la base de datos.")
        else: self.generar_filas_usuarios(self.ids.cliente_spinner.text)

    def limpiar_pantalla(self):
        self.ids.buscador_general.text = ""
        self.ids.cliente_spinner.text = "Seleccionar cliente"
        self.ids.cliente_spinner.values = self.clientes_full.copy()
        self.ids.contenedor_usuarios.clear_widgets()
        self.entradas_dinamicas.clear()
        self.ids.label_ultimo.text = "Pantalla lista"

    def popup(self, titulo, texto):
        Popup(title=titulo, content=Label(text=texto), size_hint=(0.7, 0.3)).open()