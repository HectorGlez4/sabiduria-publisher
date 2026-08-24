# Eliminación de datos — SabiduriaBolsilloPost

> Esta página existe además de
> [sabiduria.work-it.fr/datos.html](https://sabiduria.work-it.fr/datos.html),
> que es la misma información y la que leen las personas. Meta exige poder
> *rastrear* la URL de eliminación de datos, y su rastreador recibe un 403 de
> GitHub Pages. Desde github.com sí la lee, así que la URL registrada en la
> app apunta aquí. Si alguna vez cambia una, cambia la otra.

`SabiduriaBolsilloPost` **no recopila datos personales de terceros**. Es una
herramienta de publicación de uso propio: publica en las cuentas de su propio
operador y no tiene usuarios además de él. Ver la
[política de privacidad](https://sabiduria.work-it.fr/privacidad.html).

Por eso no existe ningún dato de tercero que eliminar. Aun así, aquí están las
instrucciones explícitas para borrar todo lo que la aplicación llega a tocar.

## Si eres el operador de la aplicación

**1 · Revocar el acceso de la aplicación.** En Facebook: *Configuración y
privacidad → Configuración → Aplicaciones y sitios web → SabiduriaBolsilloPost
→ Eliminar*. Esto invalida de inmediato todos los tokens emitidos para la
aplicación; a partir de ese momento no puede publicar nada.

**2 · Borrar las credenciales guardadas.** En este repositorio: *Settings →
Secrets and variables → Actions*, y eliminar `SDB_PAGE_ID`, `SDB_PAGE_TOKEN`,
`SDB_IG_USER_ID`, `SDB_THREADS_USER_ID` y `SDB_THREADS_TOKEN`.

**3 · Borrar el registro de publicaciones.** Los identificadores y enlaces de
lo ya publicado están en `content/published/`. Basta con borrar ese directorio
y confirmar el cambio.

**4 · Borrar las publicaciones ya salidas.** Pertenecen a las cuentas de
Facebook, Instagram y Threads, no a la aplicación. Se borran desde cada red,
como cualquier otra publicación.

## Si crees que tienes datos en esta aplicación

No los tienes: la aplicación no lee ni guarda información de personas ajenas a
su operador. Si aun así quieres comprobarlo o pedir una eliminación, escribe a
**hector.gonzalez@work-it.fr** y se responderá en un plazo máximo de 30 días.
