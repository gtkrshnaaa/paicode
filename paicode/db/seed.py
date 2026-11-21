def seed_provider_presets(conn) -> list[str]:
    from ..providers.presets import PRESETS

    names = []
    for order, (name, preset) in enumerate(PRESETS.items(), start=1):
        conn.execute(
            """
            INSERT INTO provider_presets (name, base_url, default_model, models_url, sort_order)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                base_url = excluded.base_url,
                default_model = excluded.default_model,
                models_url = excluded.models_url,
                sort_order = excluded.sort_order
            """,
            (name, preset.base_url, preset.model, preset.models_url, order),
        )
        names.append(name)
    return names
