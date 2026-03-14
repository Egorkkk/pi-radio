from models import Genre, Station


def build_sample_genres() -> tuple[Genre, ...]:
    return (
        Genre(
            id="synth",
            name="SYNTH",
            stations=(
                Station("synthwave", "SYNTHWAVE"),
                Station("dreamwave", "DREAMWAVE"),
                Station("outrun", "OUTRUN FM"),
                Station("retrowave", "RETROWAVE"),
                Station("cyber", "CYBER NIGHTS"),
            ),
        ),
        Genre(
            id="jazz",
            name="JAZZ",
            stations=(
                Station("smooth", "SMOOTH JAZZ"),
                Station("fusion", "JAZZ FUSION"),
                Station("night", "MIDNIGHT JAZZ"),
                Station("bebop", "BEBOP CLUB"),
            ),
        ),
        Genre(
            id="ambient",
            name="AMBIENT",
            stations=(
                Station("deep", "DEEP AMBIENT"),
                Station("space", "SPACE DRIFT"),
                Station("drone", "DRONE ZONE"),
                Station("rain", "RAIN ROOM"),
            ),
        ),
        Genre(
            id="rock",
            name="ROCK",
            stations=(
                Station("classic", "CLASSIC ROCK"),
                Station("garage", "GARAGE RADIO"),
                Station("alt", "ALT ROCK"),
                Station("desert", "DESERT DRIVE"),
            ),
        ),
        Genre(
            id="world",
            name="WORLD",
            stations=(
                Station("balkan", "BALKAN GROOVES"),
                Station("orient", "ORIENT NIGHTS"),
                Station("afro", "AFRO RHYTHMS"),
                Station("latin", "LATIN CRUISE"),
            ),
        ),
    )