from db import get_conn
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from util_db import stock_todos
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

class CreditosScreen(Screen):
    resumen_texto = StringProperty("")

    def on_pre_enter(self):
        self.ids.sistema_spinner.text = "ItvOpen"
        self.ids.packs.text = "1"
        self.ids.obs.text = ""
        self.calcular()
        self.cargar_historial()
        stocks = stock_todos()
        self.ids.fecha_input.text = datetime.now().strftime("%d/%m/%Y")
        # ... (tus líneas de inicialización de siempre) ...
        self.ids.creditos.readonly = False  # <--- AHORA PODÉS ESCRIBIR LA CANTIDAD
        self.ids.costo.readonly = False     # <--- AHORA PODÉS ESCRIBIR EL PRECIO REAL

    def calcular(self):
        sistema = self.ids.sistema_spinner.text

        if sistema == "ItvOpen":
            packs = int(self.ids.packs.text) if self.ids.packs.text else 1
            creditos = packs * 10
            costo = creditos * 550
        else:
            packs = 1
            creditos = 30
            costo = 45000

        self.ids.creditos.text = str(creditos)
        self.ids.costo.text = f"$ {costo}"

    def registrar_compra(self):

        sistema = self.ids.sistema_spinner.text

        # Leemos el número final que quedó en el cuadro
        creditos_texto = self.ids.creditos.text.strip()
        costo_texto = self.ids.costo.text.replace("$", "").strip()

        if not creditos_texto or not costo_texto:
            self.popup("Error", "Cargá cantidad y costo real")
            return

        try:
            creditos = int(creditos_texto)
            costo = float(costo_texto)

            fecha_texto = self.ids.fecha_input.text.strip()
            fecha_sql = datetime.strptime(
                fecha_texto,
                "%d/%m/%Y"
            ).strftime("%Y-%m-%d")

        except:
            self.popup("Error", "Revisá los números o la fecha")
            return

        obs = self.ids.obs.text.strip()

        conn = get_conn()
        cur = conn.cursor()

        # Si editás o creás nuevo
        if hasattr(self, "id_editando"):

            cur.execute("""
                UPDATE creditos_compras
                SET fecha=?,
                    sistema=?,
                    cantidad_creditos=?,
                    costo_total=?,
                    observaciones=?
                WHERE id=?
            """, (
                fecha_sql,
                sistema,
                creditos,
                costo,
                obs,
                self.id_editando
            ))

            del self.id_editando

        else:

            cur.execute("""
                INSERT INTO creditos_compras
                (
                    fecha,
                    sistema,
                    cantidad_creditos,
                    costo_total,
                    observaciones
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                fecha_sql,
                sistema,
                creditos,
                costo,
                obs
            ))

        # Obtenemos el ID de la compra recién creada
        compra_id = cur.lastrowid

        # Registramos el ingreso al stock
        cur.execute("""
            INSERT INTO movimientos_creditos (
                fecha,
                sistema,
                tipo,
                creditos,
                usuario_id,
                compra_id,
                observacion
            )
            VALUES (?,?,?,?,?,?,?)
        """, (
            fecha_sql,
            sistema,
            "COMPRA",
            creditos,
            None,
            compra_id,
            obs
        ))

        conn.commit()
        conn.close()

        self.cargar_historial()

        self.popup(
            "Éxito",
            f"Registrados {creditos} créditos por ${costo}"
        )

    def cargar_historial(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, fecha, sistema, cantidad_creditos, costo_total
            FROM creditos_compras
            ORDER BY fecha DESC
        """)

        filas = cur.fetchall()
        conn.close()

        contenedor = self.ids.historial_box
        contenedor.clear_widgets()

        for fila in filas:
            texto = f"{fila[1]} | {fila[2]} | {fila[3]} créditos | $ {fila[4]}"

            from kivy.uix.button import Button

            btn = Button(
                text=texto,
                size_hint_y=None,
                height=40
            )

            btn.bind(on_press=lambda x, f=fila: self.cargar_para_editar(f))
            contenedor.add_widget(btn)

    def cargar_para_editar(self, fila):
        fecha_mostrar = datetime.strptime(fila[1], "%Y-%m-%d").strftime("%d/%m/%Y")
        self.ids.fecha_input.text = fecha_mostrar
        
        self.id_editando = fila[0]

        self.ids.sistema_spinner.text = fila[2]
        self.ids.creditos.text = str(fila[3])
        self.ids.costo.text = f"$ {fila[4]}"
        self.ids.obs.text = fila[5] if fila[5] else ""

        self.popup("Modo edición", "Registro cargado para modificar")
    
    def modificar_registro(self):
        if not self.ids.id_modificar.text:
            self.popup("Error", "Ingresá ID")
            return

        registro_id = int(self.ids.id_modificar.text)

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT fecha, sistema, cantidad_creditos, costo_total, observaciones
            FROM creditos_compras
            WHERE id = ?
        """, (registro_id,))

        fila = cur.fetchone()
        conn.close()

        if not fila:
            self.popup("Error", "ID no encontrado")
            return

        # Cargar datos en los campos
        self.ids.sistema_spinner.text = fila[1]
        self.ids.creditos.text = str(fila[2])
        self.ids.costo.text = f"$ {fila[3]}"
        self.ids.obs.text = fila[4] if fila[4] else ""

        # Guardamos ID actual para actualizar después
        self.id_editando = registro_id

    def guardar_ajuste_stock(
            self,
            popup,
            sp_sistema,
            sp_tipo,
            txt_creditos,
            txt_obs):

        try:

            creditos = int(txt_creditos.text)

            if creditos <= 0:
                self.popup("Error","La cantidad debe ser mayor a cero.")
                return

            if sp_tipo.text == "Descontar":
                creditos *= -1

            conn = get_conn()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO movimientos_creditos(
                    fecha,
                    sistema,
                    tipo,
                    creditos,
                    usuario_id,
                    compra_id,
                    observacion
                )
                VALUES(?,?,?,?,?,?,?)
            """,(
                datetime.now().strftime("%d/%m/%Y"),
                sp_sistema.text,
                "AJUSTE",
                creditos,
                None,
                None,
                txt_obs.text.strip()
            ))

            conn.commit()
            conn.close()

            popup.dismiss()

            self.popup(
                "Éxito",
                "El ajuste fue registrado correctamente."
            )

            # Si tenés un método que refresca la pantalla de créditos,
            # llamalo acá.
            # self.cargar_datos()

        except Exception as e:

            self.popup(
                "Error",
                str(e)
            )
    
    def popup_ajuste_stock(self):

        layout = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=10
        )

        layout.add_widget(Label(text="Sistema"))

        sp_sistema = Spinner(
            text="Impakto",
            values=("Impakto", "IPTV", "ItvOpen", "IKS81W"),
            size_hint_y=None,
            height=40
        )

        layout.add_widget(sp_sistema)

        layout.add_widget(Label(text="Cantidad de créditos"))

        txt_creditos = TextInput(
            text="1",
            multiline=False,
            input_filter="int",
            size_hint_y=None,
            height=40
        )

        layout.add_widget(txt_creditos)

        layout.add_widget(Label(text="Tipo de ajuste"))

        sp_tipo = Spinner(
            text="Agregar",
            values=("Agregar", "Descontar"),
            size_hint_y=None,
            height=40
        )

        layout.add_widget(sp_tipo)

        layout.add_widget(Label(text="Observación"))

        txt_obs = TextInput(
            multiline=False,
            size_hint_y=None,
            height=40
        )

        layout.add_widget(txt_obs)

        botones = BoxLayout(
            size_hint_y=None,
            height=45,
            spacing=10
        )

        btn_guardar = Button(text="Guardar")
        btn_cancelar = Button(text="Cancelar")

        botones.add_widget(btn_guardar)
        botones.add_widget(btn_cancelar)

        layout.add_widget(botones)

        popup = Popup(
            title="Ajuste de Stock",
            content=layout,
            size_hint=(0.60,0.75),
            auto_dismiss=False
        )

        btn_cancelar.bind(on_release=popup.dismiss)

        btn_guardar.bind(
            on_release=lambda x:
                self.guardar_ajuste_stock(
                    popup,
                    sp_sistema,
                    sp_tipo,
                    txt_creditos,
                    txt_obs
                )
        )

        popup.open()
    
    def popup(self, titulo, texto):
        Popup(
            title=titulo,
            content=Label(text=texto),
            size_hint=(0.7, 0.3),
            auto_dismiss=True
        ).open()