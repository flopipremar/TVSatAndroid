from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ListProperty
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from datetime import datetime
import calendar
from db import get_conn

class ClientesScreen(Screen):
    cliente_seleccionado_id = None
    cliente_selected_id_temp = None
    lista_spinners_asociar = []
    lista_vendedores = ListProperty([])
    entradas_cuentas = []

    def on_pre_enter(self):
        """ Al entrar, carga la lista y resetea el formulario """
        self.cargar_clientes()
        self.cargar_vendedores()
        self.limpiar_campos()

    def cargar_vendedores(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nombre
            FROM vendedores
            WHERE activo = 1
            ORDER BY nombre
        """)

        filas = cur.fetchall()
        conn.close()

        self.lista_vendedores = ["Sin vendedor"] + [
            f"{fila[0]} - {fila[1]}" for fila in filas
        ]
    
    def filtrar_clientes(self, texto):

        texto = texto.lower().strip()

        self.ids.lista_clientes_container.clear_widgets()

        conn = get_conn()
        cur = conn.cursor()

        if texto == "":
            cur.execute("""
                SELECT id,nombre,telefono,direccion,
                    fecha_vencimiento,importe,
                    dispositivos,obs,vendedor_id
                FROM clientes
                WHERE activo=1
                ORDER BY nombre
            """)
        else:
            cur.execute("""
                SELECT id,nombre,telefono,direccion,
                    fecha_vencimiento,importe,
                    dispositivos,obs,vendedor_id
                FROM clientes
                WHERE activo=1
                AND LOWER(nombre) LIKE ?
                ORDER BY nombre
            """,(f"%{texto}%",))

        filas = cur.fetchall()
        conn.close()

        for c in filas:
            btn = Button(
                text=f"{c[1]}  |  Vence: {c[4]}  |  $ {c[5]}",
                size_hint_y=None,
                height=dp(45),
                halign="left",
                padding=(dp(10),0),
                background_normal="",
                background_color=(0.2,0.2,0.25,1)
            )

            btn.bind(on_release=lambda btn,datos=c:self.seleccionar_cliente(datos))
            self.ids.lista_clientes_container.add_widget(btn)
    
    def cargar_clientes(self):
        self.ids.lista_clientes_container.clear_widgets()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, telefono, direccion, fecha_vencimiento, importe, dispositivos, obs, vendedor_id FROM clientes WHERE activo=1 ORDER BY nombre")
        filas = cur.fetchall()
        conn.close()

        for c in filas:
            btn = Button(text=f"{c[1]}  |  Vence: {c[4]}  |  $ {c[5]}", size_hint_y=None, height=dp(45), halign="left", padding=(dp(10), 0), background_normal='', background_color=(0.2, 0.2, 0.25, 1))
            btn.bind(on_release=lambda btn, datos=c: self.seleccionar_cliente(datos))
            self.ids.lista_clientes_container.add_widget(btn)

    def seleccionar_cliente(self, datos):
        self.cliente_seleccionado_id = datos[0]
        self.ids.nombre.text = str(datos[1]); self.ids.telefono.text = str(datos[2])
        self.ids.direccion.text = str(datos[3]); self.ids.importe.text = str(datos[5])
        self.ids.dispositivos.text = str(datos[6]); self.ids.obs.text = str(datos[7])
        
        if "/" in str(datos[4]):
            p = str(datos[4]).split("/")
            self.ids.venc_dia.text = p[0]; self.ids.venc_mes.text = p[1]; self.ids.venc_anio.text = p[2]
        self.actualizar_historial_pagos()

        if datos[8]:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT nombre FROM vendedores WHERE id=?", (datos[8],))
            fila = cur.fetchone()
            conn.close()

            if fila:
                self.ids.vendedor_spinner.text = f"{datos[8]} - {fila[0]}"
        else:
            self.ids.vendedor_spinner.text = "Sin vendedor"

    def guardar_cliente(self):
        nombre = self.ids.nombre.text.strip()
        importe = self.ids.importe.text.strip()
        vencimiento = f"{self.ids.venc_dia.text.zfill(2)}/{self.ids.venc_mes.text.zfill(2)}/{self.ids.venc_anio.text}"

        if not nombre or not importe:
            self.popup("Error", "Nombre e importe son obligatorios")
            return

        # Obtener vendedor seleccionado
        vendedor = None
        if self.ids.vendedor_spinner.text != "Sin vendedor":
            vendedor = int(self.ids.vendedor_spinner.text.split(" - ")[0])

        es_nuevo = self.cliente_seleccionado_id is None

        try:
            conn = get_conn()
            cur = conn.cursor()

            if not es_nuevo:
                cur.execute("""
                    UPDATE clientes
                    SET nombre=?,
                        telefono=?,
                        direccion=?,
                        fecha_vencimiento=?,
                        importe=?,
                        dispositivos=?,
                        obs=?,
                        vendedor_id=?
                    WHERE id=?
                """, (
                    nombre,
                    self.ids.telefono.text,
                    self.ids.direccion.text,
                    vencimiento,
                    float(importe),
                    int(self.ids.dispositivos.text or 1),
                    self.ids.obs.text,
                    vendedor,
                    self.cliente_seleccionado_id
                ))

                self.cliente_selected_id_temp = self.cliente_seleccionado_id

            else:
                cur.execute("""
                    INSERT INTO clientes
                    (nombre, telefono, direccion, fecha_vencimiento,
                    importe, dispositivos, obs, vendedor_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nombre,
                    self.ids.telefono.text,
                    self.ids.direccion.text,
                    vencimiento,
                    float(importe),
                    int(self.ids.dispositivos.text or 1),
                    self.ids.obs.text,
                    vendedor
                ))

                self.cliente_selected_id_temp = cur.lastrowid

            conn.commit()
            conn.close()

            self.cargar_clientes()

            if es_nuevo:
                self.abrir_asistente_paso1_sistema()
            else:
                self.popup("OK", "Cliente actualizado")
                self.limpiar_campos()

        except Exception as e:
            self.popup("Error DB", str(e))

    # --- ASISTENTE DE CUENTAS ---
    def abrir_asistente_paso1_sistema(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        layout.add_widget(Label(text="Seleccione el Sistema:", bold=True))
        for s in ["ItvOpen", "Impakto", "IPTV"]:
            btn = Button(text=s, size_hint_y=None, height=dp(50))
            btn.bind(on_release=lambda x, sist=s: self.abrir_asistente_paso2_metodo(sist))
            layout.add_widget(btn)
        self.popup_asistente = Popup(title="Asistente - Paso 1", content=layout, size_hint=(0.8, 0.6))
        self.popup_asistente.open()

    def abrir_asistente_paso2_metodo(self, sistema):
        self.popup_asistente.dismiss()
        if sistema == "ItvOpen":
            self.abrir_gestion_cuentas_directa(sistema)
            return
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        btn_nuevo = Button(text="Crear NUEVO", background_color=(0.2, 0.6, 1, 1))
        btn_nuevo.bind(on_release=lambda x: self.abrir_gestion_cuentas_directa(sistema))
        btn_existente = Button(text="Asociar a EXISTENTE", background_color=(1, 0.6, 0.2, 1))
        btn_existente.bind(on_release=lambda x: self.abrir_asistente_paso3_asociar(sistema))
        layout.add_widget(btn_nuevo); layout.add_widget(btn_existente)
        self.popup_metodo = Popup(title=f"Paso 2 - {sistema}", content=layout, size_hint=(0.8, 0.5))
        self.popup_metodo.open()

    def abrir_asistente_paso3_asociar(self, sistema):
        if hasattr(self, 'popup_metodo'): self.popup_metodo.dismiss()
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT usuario, COUNT(id) as cant FROM usuarios WHERE sistema=? AND activo=1 GROUP BY usuario HAVING cant < 3", (sistema,))
        disponibles = cur.fetchall(); conn.close()
        if not disponibles: self.popup("Aviso", "No hay cuentas libres"); return

        opciones = [f"{d[0]} ({d[1]}/3)" for d in disponibles]
        cant_total = int(self.ids.dispositivos.text or 1)
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        scroll = ScrollView(); contenedor = GridLayout(cols=1, size_hint_y=None, spacing=dp(15))
        contenedor.bind(minimum_height=contenedor.setter('height'))
        self.lista_spinners_asociar = []
        for i in range(cant_total):
            fila = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
            fila.add_widget(Label(text=f"Disp. {i+1}:", size_hint_x=0.3))
            s = Spinner(text="Seleccionar cuenta...", values=opciones)
            fila.add_widget(s); contenedor.add_widget(fila); self.lista_spinners_asociar.append(s)
        scroll.add_widget(contenedor); layout.add_widget(scroll)
        btn = Button(text="ASOCIAR TODOS", size_hint_y=None, height=dp(55), background_color=(0.2, 0.8, 0.2, 1))
        btn.bind(on_release=lambda x: self.ejecutar_asociacion_multiple(sistema))
        layout.add_widget(btn)
        self.popup_asociar = Popup(title="Asociación Múltiple", content=layout, size_hint=(0.95, 0.8)); self.popup_asociar.open()

    def ejecutar_asociacion_multiple(self, sistema):
        conteo_en_pantalla = {}
        for s in self.lista_spinners_asociar:
            if "Seleccionar" in s.text: self.popup("Error", "Faltan datos"); return
            u_limpio = s.text.split(" (")[0].strip()
            conteo_en_pantalla[u_limpio] = conteo_en_pantalla.get(u_limpio, 0) + 1
        
        conn = get_conn(); cur = conn.cursor()
        for usu, cant in conteo_en_pantalla.items():
            cur.execute("SELECT COUNT(id) FROM usuarios WHERE usuario=? AND activo=1 AND sistema=?", (usu, sistema))
            ya_usados = cur.fetchone()[0] or 0
            if (ya_usados + cant) > 3:
                self.popup("Error", f"La cuenta {usu} no tiene lugar"); conn.close(); return
        
        v_cli = f"{self.ids.venc_dia.text}/{self.ids.venc_mes.text}/{self.ids.venc_anio.text}"
        try:
            for s in self.lista_spinners_asociar:
                u_real = s.text.split(" (")[0].strip()
                cur.execute("INSERT INTO usuarios (cliente_id, sistema, usuario, fecha_vencimiento, activo) VALUES (?, ?, ?, ?, 1)", (self.cliente_selected_id_temp, sistema, u_real, v_cli))
            conn.commit(); conn.close(); self.popup_asociar.dismiss(); self.limpiar_campos(); self.popup("Éxito", "Cuentas asociadas")
        except Exception as e: self.popup("Error DB", str(e))

    def abrir_gestion_cuentas_directa(self, sistema_elegido="ItvOpen"):
        if hasattr(self, 'popup_metodo'): self.popup_metodo.dismiss()
        try: cant_disp = int(self.ids.dispositivos.text or 1)
        except: cant_disp = 1
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView(); contenedor = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        contenedor.bind(minimum_height=contenedor.setter('height'))
        self.entradas_cuentas = []
        for i in range(cant_disp):
            fila = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            sis = Spinner(text=sistema_elegido, values=["ItvOpen", "Impakto", "IPTV"], size_hint_x=0.3)
            usu = TextInput(hint_text="Usuario", multiline=False)
            ven = TextInput(text=f"{self.ids.venc_dia.text}/{self.ids.venc_mes.text}/{self.ids.venc_anio.text}", size_hint_x=0.3)
            fila.add_widget(sis); fila.add_widget(usu); fila.add_widget(ven)
            contenedor.add_widget(fila); self.entradas_cuentas.append({'sistema': sis, 'usuario': usu, 'venc': ven})
        scroll.add_widget(contenedor); layout.add_widget(scroll)
        btn = Button(text="GUARDAR CUENTAS", size_hint_y=None, height=dp(50), background_color=(0.2, 0.6, 1, 1))
        btn.bind(on_release=lambda x: self.guardar_cuentas_popup(self.cliente_selected_id_temp))
        layout.add_widget(btn)
        self.popup_cuentas = Popup(title="Nuevas Cuentas", content=layout, size_hint=(0.95, 0.8)); self.popup_cuentas.open()

    def guardar_cuentas_popup(self, cliente_id):
        conn = get_conn(); cur = conn.cursor()
        try:
            cur.execute("DELETE FROM usuarios WHERE cliente_id = ?", (cliente_id,))
            for entrada in self.entradas_cuentas:
                usu = entrada['usuario'].text.strip()
                if usu: cur.execute("INSERT INTO usuarios (cliente_id, sistema, usuario, fecha_vencimiento, activo) VALUES (?, ?, ?, ?, 1)", (cliente_id, entrada['sistema'].text, usu, entrada['venc'].text))
            conn.commit(); self.popup_cuentas.dismiss(); self.limpiar_campos(); self.popup("Éxito", "Cuentas vinculadas")
        except Exception as e: self.popup("Error", str(e))
        finally: conn.close()

    # --- FUNCIONES DE APOYO ---
    def registrar_pago(self):
        if not self.cliente_seleccionado_id:
            self.popup("Error", "Seleccioná un cliente")
            return

        try:
            # ---------------------------------------------------------
            # BUSCAR DATOS DEL CLIENTE
            # ---------------------------------------------------------
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT nombre, importe, fecha_vencimiento
                FROM clientes
                WHERE id = ?
            """, (self.cliente_seleccionado_id,))

            cliente = cur.fetchone()
            conn.close()

            if not cliente:
                self.popup("Error", "No se encontró el cliente")
                return

            nombre_cliente = cliente[0]
            importe_habitual = float(cliente[1] or 0)
            venc_actual = cliente[2]

            # ---------------------------------------------------------
            # CONTENEDOR DEL POPUP
            # ---------------------------------------------------------
            layout = BoxLayout(
                orientation="vertical",
                spacing=dp(10),
                padding=dp(15)
            )

            # Cliente
            layout.add_widget(
                Label(
                    text=f"[b]Cliente:[/b] {nombre_cliente}",
                    markup=True,
                    size_hint_y=None,
                    height=dp(35)
                )
            )

            # Vencimiento actual
            layout.add_widget(
                Label(
                    text=f"Vencimiento actual: {venc_actual or 'Sin fecha'}",
                    size_hint_y=None,
                    height=dp(30)
                )
            )

            # ---------------------------------------------------------
            # CANTIDAD DE MESES
            # ---------------------------------------------------------
            fila_meses = BoxLayout(
                orientation="horizontal",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(45)
            )

            fila_meses.add_widget(
                Label(
                    text="Cantidad de meses:",
                    size_hint_x=0.55
                )
            )

            meses_input = TextInput(
                text="1",
                multiline=False,
                input_filter="int",
                halign="center",
                size_hint_x=0.45
            )

            fila_meses.add_widget(meses_input)
            layout.add_widget(fila_meses)

            # ---------------------------------------------------------
            # IMPORTE HABITUAL
            # ---------------------------------------------------------
            layout.add_widget(
                Label(
                    text=f"Importe habitual: ${importe_habitual:,.0f}",
                    size_hint_y=None,
                    height=dp(30)
                )
            )

            # ---------------------------------------------------------
            # IMPORTE A COBRAR
            # ---------------------------------------------------------
            fila_importe = BoxLayout(
                orientation="horizontal",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(45)
            )

            fila_importe.add_widget(
                Label(
                    text="Importe a cobrar:",
                    size_hint_x=0.45
                )
            )

            importe_input = TextInput(
                text=f"{importe_habitual:.0f}",
                multiline=False,
                input_filter="float",
                halign="right",
                size_hint_x=0.55
            )

            fila_importe.add_widget(importe_input)
            layout.add_widget(fila_importe)

            # ---------------------------------------------------------
            # MÉTODO DE PAGO
            # ---------------------------------------------------------
            fila_metodo = BoxLayout(
                orientation="horizontal",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(45)
            )

            fila_metodo.add_widget(
                Label(
                    text="Método de pago:",
                    size_hint_x=0.45
                )
            )

            metodo_spinner = Spinner(
                text="Transferencia",
                values=(
                    "Transferencia",
                    "Efectivo",
                    "Mercado Pago",
                    "Otro"
                ),
                size_hint_x=0.55
            )

            fila_metodo.add_widget(metodo_spinner)
            layout.add_widget(fila_metodo)

            # ---------------------------------------------------------
            # NUEVO VENCIMIENTO
            # ---------------------------------------------------------
            nuevo_vencimiento_label = Label(
                text=f"Nuevo vencimiento: {venc_actual or 'Sin fecha'}",
                size_hint_y=None,
                height=dp(40)
            )

            layout.add_widget(nuevo_vencimiento_label)

            # ---------------------------------------------------------
            # FUNCIÓN PARA CALCULAR NUEVO VENCIMIENTO
            # ---------------------------------------------------------
            def calcular_nuevo_vencimiento(*args):
                try:
                    meses = int(meses_input.text or "1")

                    if meses < 1:
                        meses = 1

                    if not venc_actual:
                        nuevo_vencimiento_label.text = (
                            "Nuevo vencimiento: Sin fecha"
                        )
                        return

                    fecha = datetime.strptime(
                        venc_actual,
                        "%d/%m/%Y"
                    )

                    mes_total = fecha.month - 1 + meses

                    nuevo_anio = (
                        fecha.year +
                        mes_total // 12
                    )

                    nuevo_mes = (
                        mes_total % 12
                    ) + 1

                    ultimo_dia = calendar.monthrange(
                        nuevo_anio,
                        nuevo_mes
                    )[1]

                    nuevo_dia = min(
                        fecha.day,
                        ultimo_dia
                    )

                    nueva_fecha = datetime(
                        nuevo_anio,
                        nuevo_mes,
                        nuevo_dia
                    )

                    nuevo_vencimiento_label.text = (
                        "Nuevo vencimiento: "
                        f"{nueva_fecha.strftime('%d/%m/%Y')}"
                    )

                except Exception:
                    nuevo_vencimiento_label.text = (
                        "Nuevo vencimiento: Fecha inválida"
                    )

            # ---------------------------------------------------------
            # CUANDO CAMBIAN LOS MESES
            # ---------------------------------------------------------
            def actualizar_importe(*args):
                try:
                    meses = int(meses_input.text or "1")

                    if meses < 1:
                        meses = 1

                    importe_calculado = (
                        importe_habitual * meses
                    )

                    importe_input.text = (
                        f"{importe_calculado:.0f}"
                    )

                    calcular_nuevo_vencimiento()

                except Exception:
                    pass

            meses_input.bind(
                text=actualizar_importe
            )

            # ---------------------------------------------------------
            # BOTONES
            # ---------------------------------------------------------
            botones = BoxLayout(
                orientation="horizontal",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(50)
            )

            boton_cancelar = Button(
                text="Cancelar"
            )

            boton_registrar = Button(
                text="Registrar Pago"
            )

            botones.add_widget(boton_cancelar)
            botones.add_widget(boton_registrar)

            layout.add_widget(botones)

            # ---------------------------------------------------------
            # CREAR POPUP
            # ---------------------------------------------------------
            popup_pago = Popup(
                title="Registrar Pago",
                content=layout,
                size_hint=(0.90, None),
                height=dp(500),
                auto_dismiss=False
            )

            # ---------------------------------------------------------
            # CANCELAR
            # ---------------------------------------------------------
            boton_cancelar.bind(
                on_release=lambda *args: popup_pago.dismiss()
            )

            # ---------------------------------------------------------
            # CONFIRMAR EL PAGO
            # ---------------------------------------------------------
            def confirmar_pago(*args):

                try:
                    meses = int(
                        meses_input.text or "0"
                    )

                    if meses < 1:
                        self.popup(
                            "Error",
                            "La cantidad de meses debe ser mayor a 0."
                        )
                        return

                    # Convertimos el importe
                    importe_texto = (
                        importe_input.text
                        .replace(",", ".")
                        .strip()
                    )

                    importe_pagado = float(
                        importe_texto
                    )

                    if importe_pagado <= 0:
                        self.popup(
                            "Error",
                            "El importe a cobrar debe ser mayor a 0."
                        )
                        return

                    if not venc_actual:
                        self.popup(
                            "Error",
                            "El cliente no tiene fecha de vencimiento."
                        )
                        return

                    # -------------------------------------------------
                    # CALCULAR NUEVO VENCIMIENTO
                    # -------------------------------------------------
                    fecha_actual = datetime.strptime(
                        venc_actual,
                        "%d/%m/%Y"
                    )

                    mes_total = (
                        fecha_actual.month - 1 + meses
                    )

                    nuevo_anio = (
                        fecha_actual.year +
                        mes_total // 12
                    )

                    nuevo_mes = (
                        mes_total % 12
                    ) + 1

                    ultimo_dia = calendar.monthrange(
                        nuevo_anio,
                        nuevo_mes
                    )[1]

                    nuevo_dia = min(
                        fecha_actual.day,
                        ultimo_dia
                    )

                    nueva_fecha = datetime(
                        nuevo_anio,
                        nuevo_mes,
                        nuevo_dia
                    )

                    proximo_vencimiento = (
                        nueva_fecha.strftime("%d/%m/%Y")
                    )

                    # -------------------------------------------------
                    # MES CORRESPONDIENTE
                    # -------------------------------------------------
                    meses_es = {
                        1: "Enero",
                        2: "Febrero",
                        3: "Marzo",
                        4: "Abril",
                        5: "Mayo",
                        6: "Junio",
                        7: "Julio",
                        8: "Agosto",
                        9: "Septiembre",
                        10: "Octubre",
                        11: "Noviembre",
                        12: "Diciembre"
                    }

                    hoy = datetime.now()

                    mes_pago = (
                        f"{meses_es[hoy.month]} "
                        f"{hoy.year}"
                    )

                    # -------------------------------------------------
                    # GUARDAR EN LA BASE
                    # -------------------------------------------------
                    conn = get_conn()
                    cur = conn.cursor()

                    cur.execute("""
                        INSERT INTO pagos (
                            cliente_id,
                            mes_correspondiente,
                            importe_pagado,
                            metodo_pago
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        self.cliente_seleccionado_id,
                        mes_pago,
                        importe_pagado,
                        metodo_spinner.text
                    ))

                    cur.execute("""
                        UPDATE clientes
                        SET fecha_vencimiento = ?
                        WHERE id = ?
                    """, (
                        proximo_vencimiento,
                        self.cliente_seleccionado_id
                    ))

                    conn.commit()
                    conn.close()

                    # -------------------------------------------------
                    # CERRAR POPUP
                    # -------------------------------------------------
                    popup_pago.dismiss()

                    # -------------------------------------------------
                    # ACTUALIZAR PANTALLA
                    # -------------------------------------------------
                    self.actualizar_historial_pagos()
                    self.cargar_clientes()

                    partes = proximo_vencimiento.split("/")

                    self.ids.venc_dia.text = partes[0]
                    self.ids.venc_mes.text = partes[1]
                    self.ids.venc_anio.text = partes[2]

                    self.popup(
                        "Éxito",
                        "Pago registrado correctamente.\n\n"
                        f"Importe cobrado: ${importe_pagado:,.0f}\n"
                        f"Meses: {meses}\n"
                        f"Nuevo vencimiento: "
                        f"{proximo_vencimiento}"
                    )

                except ValueError:
                    self.popup(
                        "Error",
                        "Revisá la cantidad de meses, "
                        "el importe y la fecha de vencimiento."
                    )

        except Exception as e:
            self.popup(
                "Error",
                str(e)
            )

        # IMPORTANTE:
        # Este es el botón que realmente guarda el pago.
        boton_registrar.bind(
            on_release=confirmar_pago
            )

        # Calcular valores iniciales
        calcular_nuevo_vencimiento()

        # Abrir popup
        popup_pago.open()

    def calcular_proximo_vencimiento(self, fecha_actual_str):
        try:
            fecha_dt = datetime.strptime(fecha_actual_str, "%d/%m/%Y")
            mes = (fecha_dt.month % 12) + 1; anio = fecha_dt.year + (1 if fecha_dt.month == 12 else 0)
            dia = min(fecha_dt.day, calendar.monthrange(anio, mes)[1])
            return datetime(anio, mes, dia).strftime("%d/%m/%Y")
        except: return fecha_actual_str

    def actualizar_historial_pagos(self):
        if not self.cliente_seleccionado_id: return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT fecha_pago, importe_pagado FROM pagos WHERE cliente_id = ? ORDER BY id DESC LIMIT 1", (self.cliente_seleccionado_id,))
        ultimo = cur.fetchone(); conn.close()
        self.ids.historial_pagos_label.text = f"Último Pago: {ultimo[0]} | ${ultimo[1]}" if ultimo else "Sin pagos registrados."

    def borrar_cliente(self):
        if not self.cliente_seleccionado_id: self.popup("Error", "Seleccioná cliente"); return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE clientes SET activo = 0 WHERE id = ?", (self.cliente_seleccionado_id,))
        cur.execute("UPDATE usuarios SET activo = 0 WHERE cliente_id = ?", (self.cliente_seleccionado_id,))
        conn.commit(); conn.close(); self.cargar_clientes(); self.limpiar_campos(); self.popup("Borrado", "Cliente y cuentas dados de baja.")

    def ir_a_usuarios(self):
        if not self.cliente_seleccionado_id: self.popup("Error", "Seleccioná cliente"); return
        from kivy.app import App
        app = App.get_running_app(); u_screen = app.root.get_screen('usuarios')
        txt = f"{self.cliente_seleccionado_id} - {self.ids.nombre.text}"
        u_screen.ids.cliente_spinner.text = txt; u_screen.generar_filas_usuarios(txt); app.root.current = 'usuarios'

    def limpiar_campos(self):
        self.cliente_seleccionado_id = None
        self.cliente_selected_id_temp = None
        self.ids.nombre.text = ""
        self.ids.telefono.text = ""
        self.ids.direccion.text = ""
        self.ids.importe.text = ""
        self.ids.obs.text = ""
        self.ids.dispositivos.text = "1"
        self.ids.historial_pagos_label.text = "Seleccione un cliente"
        
        # --- CAMBIO AQUÍ: Fecha de hoy + 1 mes por defecto ---
        hoy_str = datetime.now().strftime("%d/%m/%Y")
        venc_sugerido = self.calcular_proximo_vencimiento(hoy_str)
        
        p = venc_sugerido.split("/")
        self.ids.venc_dia.text = p[0]
        self.ids.venc_mes.text = p[1]
        self.ids.venc_anio.text = p[2]

    def popup(self, titulo, texto):
        Popup(title=titulo, content=Label(text=texto), size_hint=(0.7, 0.3)).open()