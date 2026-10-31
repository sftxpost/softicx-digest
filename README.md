# SofticX: бесплатная выжимка новостей

Каждый час GitHub сам читает шесть каналов-источников, выкидывает рекламу и повторы за сутки (бесплатной моделью OpenRouter) и обновляет файл `digest/latest.json`. Claude по расписанию читает этот файл, отбирает сильные темы, пишет посты и шлёт их в бота.

## Настройка (один раз, ~10 минут)

1. **Репозиторий.** На github.com: New repository → имя `softicx-digest` → Private → Create.
2. **Файлы.** В новом репозитории: Add file → Upload files → перетащи всё содержимое этого архива (папки `.github`, `digest` и файлы `digest.py`, `README.md`) → Commit changes.
   Если папка `.github` не загрузилась (на Mac она скрытая): Add file → Create new file → имя `.github/workflows/digest.yml` → вставь содержимое файла `digest.yml` из архива → Commit.
3. **Ключ OpenRouter.** openrouter.ai → войти → Keys → Create key → скопировать.
   В репозитории: Settings → Secrets and variables → Actions → New repository secret → Name: `OPENROUTER_API_KEY`, Secret: ключ → Add.
4. **Права на запись.** Settings → Actions → General → Workflow permissions → Read and write permissions → Save.
5. **Проверка.** Вкладка Actions → SofticX digest → Run workflow. Через минуту в репозитории появится `digest/latest.json`.
6. **Токен для Claude (только чтение).** github.com → Settings (профиля) → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token:
   - Repository access: Only select repositories → `softicx-digest`
   - Permissions → Repository permissions → Contents: Read-only
   - Expiration: 1 год → Generate → скопировать токен.
7. Пришли Claude: имя аккаунта GitHub, имя репозитория и этот токен. Он переключит автозапуск на чтение выжимки.

## Полезно знать

- Модель выбирается автоматически из бесплатных. Чтобы зафиксировать конкретную: Settings → Secrets and variables → Actions → Variables → `OPENROUTER_MODEL` = id модели (например, с суффиксом `:free`).
- Если модель не ответила, выжимка всё равно сохранится без фильтра – Claude отсеет сам.
- Бесплатный лимит OpenRouter – 50 запросов в день; скрипт тратит 1 запрос в час (15 в день).
- GitHub иногда запускает расписание с опозданием на 5–20 минут – это нормально.
