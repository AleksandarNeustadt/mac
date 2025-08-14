# PRINCIPLES
- Čist kod: male funkcije, jasna imena, bez dead-code-a.
- Tipovi: koristimo `typing` gdje je smisleno.
- Dok: svaki public modul/klasa/metoda ima docstring.
- Testovi: za novi kod obavezno dodaj PyTest test.
- Struktura: odvoji business logiku od IO slojeva.
- Error handling: nema `pass`; loguj i propagiraj smisleno.
- Config iz .env preko našeg Config modula.
