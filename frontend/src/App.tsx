import {
  FormEvent,
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
const TOKEN_STORAGE_KEY = 'cava_access_token'

type MenuVariant = {
  portion: string
  price: number
  label: string
}

type MenuItem = {
  id: number
  name: string
  name_en: string
  menu_group: string
  section: string
  description: string
  description_en: string
  ingredients: string
  ingredients_en: string
  image_url: string
  tags: string[]
  variants: MenuVariant[]
  is_available: boolean
  is_featured: boolean
  deleted_at: string | null
  deleted_via_menu: boolean
  created_at: string
  updated_at: string
}

type MenuCollection = {
  id: number
  name: string
  created_at: string
  updated_at: string
  deleted_at: string | null
  active_items: number
  deleted_items: number
}

type MenuSummary = {
  total_items: number
  available_items: number
  featured_items: number
  menu_groups: number
  sections: number
  last_updated_at: string | null
}

type MenuVariantForm = {
  portion: string
  price: string
  label: string
}

type MenuFormState = {
  name: string
  name_en: string
  menu_group: string
  section: string
  ingredients: string
  ingredients_en: string
  tags: string
  variants: MenuVariantForm[]
  is_available: boolean
  is_featured: boolean
}

type AuthenticatedUser = {
  id: number
  username: string
  full_name: string
  role: 'super_admin' | 'staff_admin'
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

type LoginResponse = {
  access_token: string
  user: AuthenticatedUser
}

type LoginFormState = {
  username: string
  password: string
}

type ToastKind = 'error' | 'success'

type ToastState = {
  message: string
  kind: ToastKind
}

type UserFormState = {
  username: string
  full_name: string
  role: 'super_admin' | 'staff_admin'
  password: string
  is_active: boolean
}

type Workspace = 'menu' | 'users'
type EditorLocale = 'ru' | 'en'
type MenuWorkspaceView = 'active' | 'deleted' | 'menus'

function createEmptyVariant(): MenuVariantForm {
  return { portion: '', price: '', label: '' }
}

function createEmptyMenuForm(menuGroup = 'Основное меню', section = 'Кофе'): MenuFormState {
  return {
    name: '',
    name_en: '',
    menu_group: menuGroup,
    section,
    ingredients: '',
    ingredients_en: '',
    tags: '',
    variants: [createEmptyVariant()],
    is_available: true,
    is_featured: false,
  }
}

function createEmptyUserForm(): UserFormState {
  return {
    username: '',
    full_name: '',
    role: 'staff_admin',
    password: '',
    is_active: true,
  }
}

function formatDate(date: string | null): string {
  if (!date) return 'Пока нет данных'
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow',
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(date))
}

function formatPrice(price: number): string {
  return `${price.toFixed(0)} RUB`
}

function formatVariants(variants: MenuVariant[]): string {
  return variants
    .map((variant) => {
      const label = variant.label.trim() ? `${variant.label}: ` : ''
      return `${label}${variant.portion} — ${formatPrice(variant.price)}`
    })
    .join(' | ')
}

function uniqueValues(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))]
}

async function requestJson<T>(
  path: string,
  init: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`
    try {
      const data = (await response.json()) as { detail?: string }
      if (data.detail) {
        message = data.detail
      }
    } catch {
      // Preserve fallback message for non-JSON responses.
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

function App() {
  const [authLoading, setAuthLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(
    () => window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? '',
  )
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null)
  const [workspace, setWorkspace] = useState<Workspace>('menu')
  const [loginForm, setLoginForm] = useState<LoginFormState>({
    username: '',
    password: '',
  })

  const [items, setItems] = useState<MenuItem[]>([])
  const [deletedItems, setDeletedItems] = useState<MenuItem[]>([])
  const [menus, setMenus] = useState<MenuCollection[]>([])
  const [sections, setSections] = useState<string[]>([])
  const [summary, setSummary] = useState<MenuSummary | null>(null)
  const [users, setUsers] = useState<AuthenticatedUser[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [usersLoading, setUsersLoading] = useState(false)
  const [userSaving, setUserSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [renderedToast, setRenderedToast] = useState<ToastState | null>(null)
  const [toastPhase, setToastPhase] = useState<'enter' | 'exit'>('enter')
  const [search, setSearch] = useState('')
  const [activeGroup, setActiveGroup] = useState('Все меню')
  const [activeSection, setActiveSection] = useState('Все разделы')
  const [menuView, setMenuView] = useState<MenuWorkspaceView>('active')
  const [isMenuEditorOpen, setIsMenuEditorOpen] = useState(false)
  const [isMenuCollectionEditorOpen, setIsMenuCollectionEditorOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingUserId, setEditingUserId] = useState<number | null>(null)
  const [editorLocale, setEditorLocale] = useState<EditorLocale>('ru')
  const [menuForm, setMenuForm] = useState<MenuFormState>(() => createEmptyMenuForm())
  const [menuCollectionName, setMenuCollectionName] = useState('')
  const [userForm, setUserForm] = useState<UserFormState>(() => createEmptyUserForm())

  const deferredSearch = useDeferredValue(search)
  const isSuperAdmin = currentUser?.role === 'super_admin'

  useEffect(() => {
    const message = error || notice
    if (!message) return

    setRenderedToast({
      message,
      kind: error ? 'error' : 'success',
    })
    setToastPhase('enter')

    const leaveTimeoutId = window.setTimeout(() => {
      setToastPhase('exit')
    }, 2600)

    const clearTimeoutId = window.setTimeout(() => {
      setRenderedToast((current) => (current?.message === message ? null : current))
      setError((current) => (current === message ? '' : current))
      setNotice((current) => (current === message ? '' : current))
    }, 3000)

    return () => {
      window.clearTimeout(leaveTimeoutId)
      window.clearTimeout(clearTimeoutId)
    }
  }, [error, notice])

  useEffect(() => {
    if (!isMenuEditorOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeMenuEditor()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMenuEditorOpen, menus, sections])

  async function restoreSession(token: string) {
    try {
      const user = await requestJson<AuthenticatedUser>('/auth/me', {}, token)
      setCurrentUser(user)
      setError('')
    } catch {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY)
      setAccessToken('')
      setCurrentUser(null)
    } finally {
      setAuthLoading(false)
    }
  }

  useEffect(() => {
    if (!accessToken) {
      setAuthLoading(false)
      return
    }

    void restoreSession(accessToken)
  }, [accessToken])

  async function loadMenuData(showRefreshNotice = false) {
    if (!currentUser) return

    setLoading(true)
    try {
      const [
        itemsResponse,
        deletedItemsResponse,
        catalogResponse,
        sectionsResponse,
        summaryResponse,
      ] =
        await Promise.all([
          requestJson<MenuItem[]>('/menu/items'),
          requestJson<MenuItem[]>('/menu/items?deleted_only=true'),
          requestJson<MenuCollection[]>('/menu/catalog'),
          requestJson<string[]>('/menu/sections'),
          requestJson<MenuSummary>('/menu/summary'),
        ])

      startTransition(() => {
        setItems(itemsResponse)
        setDeletedItems(deletedItemsResponse)
        setMenus(catalogResponse)
        setSections(sectionsResponse)
        setSummary(summaryResponse)
      })

      if (showRefreshNotice) {
        setNotice('Данные меню обновлены.')
      }
      setError('')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Не удалось загрузить данные меню.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function loadUsers() {
    if (!accessToken || !isSuperAdmin) return

    setUsersLoading(true)
    try {
      const usersResponse = await requestJson<AuthenticatedUser[]>('/auth/users', {}, accessToken)
      setUsers(usersResponse)
      setError('')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Не удалось загрузить сотрудников.',
      )
    } finally {
      setUsersLoading(false)
    }
  }

  useEffect(() => {
    if (!currentUser) return
    void loadMenuData()
  }, [currentUser])

  useEffect(() => {
    const availableGroups = menus.filter((menu) => !menu.deleted_at).map((menu) => menu.name)
    if (activeGroup !== 'Все меню' && !availableGroups.includes(activeGroup)) {
      setActiveGroup('Все меню')
    }
  }, [activeGroup, menus])

  useEffect(() => {
    if (!currentUser || !isSuperAdmin) return
    void loadUsers()
  }, [currentUser, isSuperAdmin])

  function resetMenuEditor() {
    setEditingId(null)
    setEditorLocale('ru')
    const firstActiveMenu =
      menus.find((menu) => !menu.deleted_at)?.name ?? 'Основное меню'
    setMenuForm(createEmptyMenuForm(firstActiveMenu, sections[0] ?? 'Кофе'))
  }

  function openCreateMenuEditor() {
    resetMenuEditor()
    setIsMenuEditorOpen(true)
  }

  function closeMenuEditor() {
    setIsMenuEditorOpen(false)
    resetMenuEditor()
  }

  function openMenuCollectionEditor() {
    setMenuCollectionName('')
    setIsMenuCollectionEditorOpen(true)
  }

  function closeMenuCollectionEditor() {
    setMenuCollectionName('')
    setIsMenuCollectionEditorOpen(false)
  }

  function resetUserEditor() {
    setEditingUserId(null)
    setUserForm(createEmptyUserForm())
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')

    try {
      const response = await requestJson<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      })

      window.localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token)
      setAccessToken(response.access_token)
      setCurrentUser(response.user)
      setWorkspace('menu')
      setLoginForm({ username: '', password: '' })
      setNotice(`Здравствуйте, ${response.user.full_name || response.user.username}.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось войти в систему.',
      )
    }
  }

  async function handleLogout() {
    try {
      if (accessToken) {
        await requestJson<void>(
          '/auth/logout',
          {
            method: 'POST',
          },
          accessToken,
        )
      }
    } catch {
      // Best effort logout; local cleanup still happens.
    }

    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    setAccessToken('')
    setCurrentUser(null)
    setItems([])
    setDeletedItems([])
    setMenus([])
    setUsers([])
    setNotice('')
    setError('')
    setIsMenuEditorOpen(false)
    setIsMenuCollectionEditorOpen(false)
    setWorkspace('menu')
    setMenuView('active')
    resetMenuEditor()
    resetUserEditor()
  }

  function startEditingMenuItem(item: MenuItem) {
    setIsMenuEditorOpen(true)
    setEditingId(item.id)
    setEditorLocale('ru')
    setMenuForm({
      name: item.name,
      name_en: item.name_en,
      menu_group: item.menu_group,
      section: item.section,
      ingredients: item.ingredients,
      ingredients_en: item.ingredients_en,
      tags: item.tags.join(', '),
      variants: item.variants.map((variant) => ({
        portion: variant.portion,
        price: String(variant.price),
        label: variant.label,
      })),
      is_available: item.is_available,
      is_featured: item.is_featured,
    })
  }

  function updateVariant(index: number, field: keyof MenuVariantForm, value: string) {
    setMenuForm((current) => ({
      ...current,
      variants: current.variants.map((variant, currentIndex) =>
        currentIndex === index ? { ...variant, [field]: value } : variant,
      ),
    }))
  }

  function addVariant() {
    setMenuForm((current) => ({
      ...current,
      variants: [...current.variants, createEmptyVariant()],
    }))
  }

  function removeVariant(index: number) {
    setMenuForm((current) => ({
      ...current,
      variants:
        current.variants.length === 1
          ? current.variants
          : current.variants.filter((_, currentIndex) => currentIndex !== index),
    }))
  }

  async function handleMenuSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')

    const parsedVariants = menuForm.variants
      .map((variant) => ({
        portion: variant.portion.trim(),
        price: Number(variant.price),
        label: variant.label.trim(),
      }))
      .filter((variant) => variant.portion.length > 0)

    if (!menuForm.name.trim() || !menuForm.menu_group.trim() || !menuForm.section.trim()) {
      setError('Заполните название, группу меню и раздел.')
      return
    }

    if (parsedVariants.length === 0) {
      setError('Добавьте хотя бы один вариант порции и цены.')
      return
    }

    if (parsedVariants.some((variant) => Number.isNaN(variant.price) || variant.price < 0)) {
      setError('У каждого варианта должна быть корректная цена.')
      return
    }

    const payload = {
      name: menuForm.name.trim(),
      name_en: menuForm.name_en.trim(),
      menu_group: menuForm.menu_group.trim(),
      section: menuForm.section.trim(),
      description: '',
      description_en: '',
      ingredients: menuForm.ingredients.trim(),
      ingredients_en: menuForm.ingredients_en.trim(),
      image_url: '',
      tags: menuForm.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      variants: parsedVariants,
      is_available: menuForm.is_available,
      is_featured: menuForm.is_featured,
    }

    const path = editingId === null ? '/menu/items' : `/menu/items/${editingId}`
    const method = editingId === null ? 'POST' : 'PUT'

    setSaving(true)
    try {
      await requestJson<MenuItem>(
        path,
        {
          method,
          body: JSON.stringify(payload),
        },
        accessToken,
      )
      await loadMenuData()
      closeMenuEditor()
      setError('')
      setNotice(editingId === null ? 'Позиция создана.' : 'Позиция обновлена.')
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось сохранить позицию.',
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleAvailabilityToggle(item: MenuItem) {
    try {
      await requestJson<MenuItem>(
        `/menu/items/${item.id}/availability`,
        {
          method: 'PATCH',
          body: JSON.stringify({ is_available: !item.is_available }),
        },
        accessToken,
      )
      await loadMenuData()
      setNotice(
        item.is_available
          ? `Позиция "${item.name}" помечена как sold out.`
          : `Позиция "${item.name}" снова доступна.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Не удалось обновить availability.',
      )
    }
  }

  async function handleDeleteMenuItem(item: MenuItem) {
    const shouldDelete = window.confirm(`Переместить "${item.name}" в удалённые блюда?`)
    if (!shouldDelete) return

    try {
      await requestJson<void>(
        `/menu/items/${item.id}`,
        {
          method: 'DELETE',
        },
        accessToken,
      )
      await loadMenuData()
      if (editingId === item.id) {
        closeMenuEditor()
      }
      setNotice(`Позиция "${item.name}" перемещена в удалённые.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось удалить позицию.',
      )
    }
  }

  async function handleRestoreMenuItem(item: MenuItem) {
    try {
      await requestJson<MenuItem>(
        `/menu/items/${item.id}/restore`,
        {
          method: 'POST',
        },
        accessToken,
      )
      await loadMenuData()
      setNotice(`Позиция "${item.name}" возвращена в меню.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось вернуть позицию.',
      )
    }
  }

  async function handleMenuCollectionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')

    if (!menuCollectionName.trim()) {
      setError('Укажите название нового меню.')
      return
    }

    setSaving(true)
    try {
      await requestJson<MenuCollection>(
        '/menu/catalog',
        {
          method: 'POST',
          body: JSON.stringify({ name: menuCollectionName.trim() }),
        },
        accessToken,
      )
      await loadMenuData()
      closeMenuCollectionEditor()
      setNotice(`Меню "${menuCollectionName.trim()}" создано.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось создать меню.',
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteMenuCollection(menu: MenuCollection) {
    const shouldDelete = window.confirm(
      `Архивировать меню "${menu.name}" и переместить его блюда в удалённые?`,
    )
    if (!shouldDelete) return

    try {
      await requestJson<void>(
        `/menu/catalog/${menu.id}`,
        {
          method: 'DELETE',
        },
        accessToken,
      )
      await loadMenuData()
      setNotice(`Меню "${menu.name}" архивировано.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось удалить меню.',
      )
    }
  }

  async function handleRestoreMenuCollection(menu: MenuCollection) {
    try {
      await requestJson<MenuCollection>(
        `/menu/catalog/${menu.id}/restore`,
        {
          method: 'POST',
        },
        accessToken,
      )
      await loadMenuData()
      setNotice(`Меню "${menu.name}" восстановлено.`)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось вернуть меню.',
      )
    }
  }

  function startEditingUser(user: AuthenticatedUser) {
    setEditingUserId(user.id)
    setUserForm({
      username: user.username,
      full_name: user.full_name,
      role: user.role,
      password: '',
      is_active: user.is_active,
    })
    setWorkspace('users')
  }

  async function handleUserSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')

    if (!isSuperAdmin) {
      setError('Только главный администратор может управлять сотрудниками.')
      return
    }

    if (!userForm.username.trim()) {
      setError('Укажите username сотрудника.')
      return
    }

    if (editingUserId === null && userForm.password.trim().length < 8) {
      setError('Пароль нового сотрудника должен быть не короче 8 символов.')
      return
    }

    const path = editingUserId === null ? '/auth/users' : `/auth/users/${editingUserId}`
    const method = editingUserId === null ? 'POST' : 'PATCH'

    const payload =
      editingUserId === null
        ? {
            username: userForm.username.trim(),
            full_name: userForm.full_name.trim(),
            role: userForm.role,
            password: userForm.password.trim(),
            is_active: userForm.is_active,
          }
        : {
            full_name: userForm.full_name.trim(),
            role: userForm.role,
            is_active: userForm.is_active,
            ...(userForm.password.trim()
              ? { password: userForm.password.trim() }
              : {}),
          }

    setUserSaving(true)
    try {
      const updatedUser = await requestJson<AuthenticatedUser>(
        path,
        {
          method,
          body: JSON.stringify(payload),
        },
        accessToken,
      )
      await loadUsers()
      if (currentUser && updatedUser.id === currentUser.id) {
        setCurrentUser(updatedUser)
      }
      resetUserEditor()
      setError('')
      setNotice(
        editingUserId === null
          ? `Пользователь "${updatedUser.username}" создан.`
          : `Данные пользователя "${updatedUser.username}" обновлены.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось сохранить пользователя.',
      )
    } finally {
      setUserSaving(false)
    }
  }

  async function toggleUserActive(user: AuthenticatedUser) {
    if (!isSuperAdmin) return

    try {
      const updatedUser = await requestJson<AuthenticatedUser>(
        `/auth/users/${user.id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ is_active: !user.is_active }),
        },
        accessToken,
      )
      await loadUsers()
      if (currentUser && updatedUser.id === currentUser.id) {
        setCurrentUser(updatedUser)
      }
      setNotice(
        updatedUser.is_active
          ? `Доступ для "${updatedUser.username}" снова открыт.`
          : `Доступ для "${updatedUser.username}" отключен.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Не удалось обновить доступ.',
      )
    }
  }

  const activeMenus = useMemo(
    () => menus.filter((menu) => !menu.deleted_at),
    [menus],
  )
  const itemSource = menuView === 'deleted' ? deletedItems : items

  const visibleGroups = useMemo(() => {
    if (menuView === 'menus') {
      return []
    }
    return uniqueValues(itemSource.map((item) => item.menu_group))
  }, [itemSource, menuView])

  const visibleSections = useMemo(() => {
    if (menuView === 'menus') {
      return []
    }
    const scopedItems =
      activeGroup === 'Все меню'
        ? itemSource
        : itemSource.filter((item) => item.menu_group === activeGroup)
    return uniqueValues(scopedItems.map((item) => item.section))
  }, [activeGroup, itemSource, menuView])

  useEffect(() => {
    if (menuView === 'menus') {
      setActiveSection('Все разделы')
      return
    }

    if (activeGroup !== 'Все меню' && !visibleGroups.includes(activeGroup)) {
      setActiveGroup('Все меню')
      setActiveSection('Все разделы')
      return
    }

    if (activeSection !== 'Все разделы' && !visibleSections.includes(activeSection)) {
      setActiveSection('Все разделы')
    }
  }, [activeGroup, activeSection, menuView, visibleGroups, visibleSections])

  const normalizedSearch = deferredSearch.trim().toLowerCase()
  const visibleItems = itemSource.filter((item) => {
    const groupMatches = activeGroup === 'Все меню' || item.menu_group === activeGroup
    const sectionMatches = activeSection === 'Все разделы' || item.section === activeSection
    const searchMatches =
      normalizedSearch.length === 0 ||
      item.name.toLowerCase().includes(normalizedSearch) ||
      item.name_en.toLowerCase().includes(normalizedSearch) ||
      item.menu_group.toLowerCase().includes(normalizedSearch) ||
      item.section.toLowerCase().includes(normalizedSearch) ||
      item.ingredients.toLowerCase().includes(normalizedSearch) ||
      item.ingredients_en.toLowerCase().includes(normalizedSearch) ||
      item.description.toLowerCase().includes(normalizedSearch) ||
      item.description_en.toLowerCase().includes(normalizedSearch)

    return groupMatches && sectionMatches && searchMatches
  })

  const visibleCatalog = (menuView === 'menus' ? menus : []).filter((menu) => {
    if (!normalizedSearch) return true
    return menu.name.toLowerCase().includes(normalizedSearch)
  })

  const toastClassName = renderedToast
    ? `toast ${renderedToast.kind} ${toastPhase === 'exit' ? 'is-leaving' : 'is-visible'}`
    : ''

  const menuEditorModal = isMenuEditorOpen ? (
    <div className="modal-backdrop" onClick={closeMenuEditor}>
      <div className="modal-card editor-panel" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <div>
            <p className="eyebrow">Редактор меню</p>
            <h2>{editingId === null ? 'Новая позиция' : `Редактирование #${editingId}`}</h2>
          </div>
          <button type="button" className="modal-close" onClick={closeMenuEditor}>
            Закрыть
          </button>
        </div>

        <form className="editor-form" onSubmit={handleMenuSubmit}>
          <div className="two-column">
            <label>
              Группа меню
              <input
                type="text"
                list="group-options"
                value={menuForm.menu_group}
                onChange={(event) =>
                  setMenuForm((current) => ({ ...current, menu_group: event.target.value }))
                }
                placeholder="Весеннее меню"
              />
              <datalist id="group-options">
                {activeMenus.map((menu) => (
                  <option key={menu.id} value={menu.name} />
                ))}
              </datalist>
            </label>

            <label>
              Раздел
              <input
                type="text"
                list="section-options"
                value={menuForm.section}
                onChange={(event) =>
                  setMenuForm((current) => ({ ...current, section: event.target.value }))
                }
                placeholder="Вторые блюда"
              />
              <datalist id="section-options">
                {sections.map((section) => (
                  <option key={section} value={section} />
                ))}
              </datalist>
            </label>
          </div>

          <div className="locale-panel">
            <div className="locale-tabs">
              <button
                type="button"
                className={editorLocale === 'ru' ? 'chip active' : 'chip'}
                onClick={() => setEditorLocale('ru')}
              >
                Русский
              </button>
              <button
                type="button"
                className={editorLocale === 'en' ? 'chip active' : 'chip'}
                onClick={() => setEditorLocale('en')}
              >
                English
              </button>
            </div>

            <p className="panel-status subtle">
              Английские поля используются Telegram-ботом, когда пользователь выбирает English.
            </p>
          </div>

          {editorLocale === 'ru' ? (
            <>
              <label>
                Название блюда или напитка
                <input
                  type="text"
                  value={menuForm.name}
                  onChange={(event) =>
                    setMenuForm((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Паста Тейсти"
                />
              </label>

              <label>
                Ингредиенты / состав
                <textarea
                  rows={5}
                  value={menuForm.ingredients}
                  onChange={(event) =>
                    setMenuForm((current) => ({
                      ...current,
                      ingredients: event.target.value,
                    }))
                  }
                  placeholder="Моцарелла, томатный соус, базилик"
                />
              </label>
            </>
          ) : (
            <>
              <label>
                Dish or drink name in English
                <input
                  type="text"
                  value={menuForm.name_en}
                  onChange={(event) =>
                    setMenuForm((current) => ({ ...current, name_en: event.target.value }))
                  }
                  placeholder="Tasty Pasta"
                />
              </label>

              <label>
                Ingredients in English
                <textarea
                  rows={5}
                  value={menuForm.ingredients_en}
                  onChange={(event) =>
                    setMenuForm((current) => ({
                      ...current,
                      ingredients_en: event.target.value,
                    }))
                  }
                  placeholder="Mozzarella, tomato sauce, basil"
                />
              </label>
            </>
          )}

          <label>
            Теги через запятую
            <input
              type="text"
              value={menuForm.tags}
              onChange={(event) =>
                setMenuForm((current) => ({ ...current, tags: event.target.value }))
              }
              placeholder="seasonal, new, bestseller"
            />
          </label>

          <div className="variant-editor">
            <div className="section-head compact">
              <div>
                <p className="eyebrow">Порции и цены</p>
                <h2>Варианты</h2>
              </div>
              <button type="button" className="btn btn-secondary" onClick={addVariant}>
                Добавить вариант
              </button>
            </div>

            {menuForm.variants.map((variant, index) => (
              <div className="variant-row" key={`variant-${index}`}>
                <label className="variant-field">
                  <span className="variant-field-label">Метка</span>
                  <input
                    type="text"
                    value={variant.label}
                    onChange={(event) => updateVariant(index, 'label', event.target.value)}
                    placeholder="Например: стандарт"
                  />
                </label>

                <label className="variant-field">
                  <span className="variant-field-label">Порция / объём</span>
                  <input
                    type="text"
                    value={variant.portion}
                    onChange={(event) => updateVariant(index, 'portion', event.target.value)}
                    placeholder="250 мл / 520 гр"
                  />
                </label>

                <label className="variant-field">
                  <span className="variant-field-label">Цена</span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={variant.price}
                    onChange={(event) => updateVariant(index, 'price', event.target.value)}
                    placeholder="350"
                  />
                </label>

                <button
                  type="button"
                  className="btn btn-danger slim-btn"
                  onClick={() => removeVariant(index)}
                  disabled={menuForm.variants.length === 1}
                >
                  Удалить
                </button>
              </div>
            ))}
          </div>

          <div className="two-column">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={menuForm.is_available}
                onChange={(event) =>
                  setMenuForm((current) => ({
                    ...current,
                    is_available: event.target.checked,
                  }))
                }
              />
              Сейчас доступно
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={menuForm.is_featured}
                onChange={(event) =>
                  setMenuForm((current) => ({
                    ...current,
                    is_featured: event.target.checked,
                  }))
                }
              />
              Показать как featured
            </label>
          </div>

          <div className="editor-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Сохранение...' : editingId === null ? 'Создать' : 'Сохранить'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={resetMenuEditor}>
              Сбросить
            </button>
          </div>
        </form>
      </div>
    </div>
  ) : null

  const menuCollectionModal = isMenuCollectionEditorOpen ? (
    <div className="modal-backdrop" onClick={closeMenuCollectionEditor}>
      <div className="modal-card editor-panel narrow-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <div>
            <p className="eyebrow">Каталог меню</p>
            <h2>Новое меню</h2>
          </div>
          <button type="button" className="modal-close" onClick={closeMenuCollectionEditor}>
            Закрыть
          </button>
        </div>

        <form className="editor-form" onSubmit={handleMenuCollectionSubmit}>
          <label>
            Название меню
            <input
              type="text"
              value={menuCollectionName}
              onChange={(event) => setMenuCollectionName(event.target.value)}
              placeholder="Летнее меню"
            />
          </label>

          <div className="editor-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Создание...' : 'Создать меню'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={closeMenuCollectionEditor}
            >
              Отмена
            </button>
          </div>
        </form>
      </div>
    </div>
  ) : null

  if (authLoading) {
    return <div className="login-shell">Проверяем сессию...</div>
  }

  if (!currentUser) {
    return (
      <>
        <div className="login-shell">
          <div className="login-card">
            <p className="eyebrow">Cava Staff Access</p>
            <h1>Вход в админ-панель</h1>
            <p className="hero-description">
              Доступ к сайту открыт только сотрудникам Cava. Войдите по логину и паролю,
              выданным главным администратором.
            </p>

            <form className="login-form" onSubmit={handleLogin}>
              <label>
                Логин
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={(event) =>
                    setLoginForm((current) => ({ ...current, username: event.target.value }))
                  }
                  placeholder="owner"
                />
              </label>

              <label>
                Пароль
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(event) =>
                    setLoginForm((current) => ({ ...current, password: event.target.value }))
                  }
                  placeholder="********"
                />
              </label>

              <button type="submit" className="btn btn-primary wide-btn">
                Войти
              </button>
            </form>
          </div>
        </div>
        {renderedToast ? <div className={toastClassName}>{renderedToast.message}</div> : null}
      </>
    )
  }

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Cava Cafe Operations</p>
          <h1>Cava Menu Control</h1>
          <p className="hero-description">
            Закрытая staff-only панель для управления меню и, для главного
            администратора, выдачи доступа сотрудникам.
          </p>

          <div className="summary-grid">
            <article className="summary-card">
              <span>Всего позиций</span>
              <strong>{summary?.total_items ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>В наличии</span>
              <strong>{summary?.available_items ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Групп меню</span>
              <strong>{summary?.menu_groups ?? 0}</strong>
            </article>
            <article className="summary-card">
              <span>Сотрудников</span>
              <strong>{isSuperAdmin ? users.length : 0}</strong>
            </article>
          </div>
        </div>

        <div className="access-panel account-panel">
          <p className="eyebrow">Текущая сессия</p>
          <h2>{currentUser.full_name || currentUser.username}</h2>
          <p className="panel-copy">
            Роль: {currentUser.role === 'super_admin' ? 'Главный администратор' : 'Сотрудник'}
          </p>
          <p className="panel-status">Логин: {currentUser.username}</p>
          <p className="panel-status subtle">
            Последний вход: {formatDate(currentUser.last_login_at)}
          </p>
          <p className="panel-status subtle">
            Аккаунт создан: {formatDate(currentUser.created_at)}
          </p>

          <div className="access-actions">
            <button
              type="button"
              className={workspace === 'menu' ? 'btn btn-primary' : 'btn btn-secondary'}
              onClick={() => setWorkspace('menu')}
            >
              Меню
            </button>
            {isSuperAdmin ? (
              <button
                type="button"
                className={workspace === 'users' ? 'btn btn-primary' : 'btn btn-secondary'}
                onClick={() => setWorkspace('users')}
              >
                Сотрудники
              </button>
            ) : null}
            <button type="button" className="btn btn-danger" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        </div>
      </header>

      {renderedToast ? <div className={toastClassName}>{renderedToast.message}</div> : null}

      {workspace === 'menu' ? (
        <>
          <section className="toolbar-panel">
            <div className="search-panel">
              <label htmlFor="search-input">Поиск по меню</label>
              <input
                id="search-input"
                type="search"
                placeholder={
                  menuView === 'menus'
                    ? 'Летнее меню, весеннее меню...'
                    : 'Кофе, паста, весеннее меню...'
                }
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <div className="chip-row">
              <button
                className={menuView === 'active' ? 'chip active' : 'chip'}
                onClick={() => setMenuView('active')}
                type="button"
              >
                Активные блюда
              </button>
              <button
                className={menuView === 'deleted' ? 'chip active' : 'chip'}
                onClick={() => setMenuView('deleted')}
                type="button"
              >
                Удалённые блюда
              </button>
              <button
                className={menuView === 'menus' ? 'chip active' : 'chip'}
                onClick={() => setMenuView('menus')}
                type="button"
              >
                Меню и сезоны
              </button>
            </div>

            <button
              type="button"
              className="btn btn-secondary refresh-btn"
              onClick={() => void loadMenuData(true)}
            >
              Обновить данные
            </button>
          </section>

          {menuView !== 'menus' ? (
            <>
              <section className="toolbar-panel secondary-toolbar">
                <div className="chip-row">
                  <button
                    className={activeGroup === 'Все меню' ? 'chip active' : 'chip'}
                    onClick={() => {
                      setActiveGroup('Все меню')
                      setActiveSection('Все разделы')
                    }}
                    type="button"
                  >
                    Все меню
                  </button>
                  {visibleGroups.map((group) => (
                    <button
                      key={group}
                      className={activeGroup === group ? 'chip active' : 'chip'}
                      onClick={() => {
                        setActiveGroup(group)
                        setActiveSection('Все разделы')
                      }}
                      type="button"
                    >
                      {group}
                    </button>
                  ))}
                </div>
              </section>

              <section className="toolbar-panel secondary-toolbar">
                <div className="chip-row">
                  <button
                    className={activeSection === 'Все разделы' ? 'chip active' : 'chip'}
                    onClick={() => setActiveSection('Все разделы')}
                    type="button"
                  >
                    Все разделы
                  </button>
                  {visibleSections.map((section) => (
                    <button
                      key={section}
                      className={activeSection === section ? 'chip active' : 'chip'}
                      onClick={() => setActiveSection(section)}
                      type="button"
                    >
                      {section}
                    </button>
                  ))}
                </div>
              </section>
            </>
          ) : null}

          <main className="workspace-grid menu-workspace">
            <section className="board-panel">
              <div className="section-head">
                <div>
                  <p className="eyebrow">
                    {menuView === 'active'
                      ? 'Живое меню'
                      : menuView === 'deleted'
                        ? 'История удалений'
                        : 'Каталог меню'}
                  </p>
                  <h2>
                    {menuView === 'active'
                      ? 'Позиции Cava'
                      : menuView === 'deleted'
                        ? 'Удалённые блюда'
                        : 'Сезонные и основные меню'}
                  </h2>
                </div>
                <div className="section-head-actions">
                  <span className="count-pill">
                    {menuView === 'menus'
                      ? `${visibleCatalog.length} меню`
                      : `${visibleItems.length} видно`}
                  </span>
                  {menuView === 'active' ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={openCreateMenuEditor}
                    >
                      Добавить блюдо
                    </button>
                  ) : null}
                  {menuView === 'menus' ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={openMenuCollectionEditor}
                    >
                      Создать меню
                    </button>
                  ) : null}
                </div>
              </div>

              {loading ? (
                <div className="empty-state">Загрузка меню...</div>
              ) : menuView === 'menus' ? (
                visibleCatalog.length === 0 ? (
                  <div className="empty-state">По текущему поиску меню не найдены.</div>
                ) : (
                  <div className="card-grid">
                    {visibleCatalog.map((menu) => (
                      <article className="menu-card menu-collection-card" key={menu.id}>
                        <div className="badge-row">
                          <span className="category-badge">
                            {menu.deleted_at ? 'Архив меню' : 'Активное меню'}
                          </span>
                          <span className="status-badge available">
                            {menu.active_items} активных
                          </span>
                          {menu.deleted_items > 0 ? (
                            <span className="status-badge unavailable">
                              {menu.deleted_items} удалённых
                            </span>
                          ) : null}
                        </div>

                        <h3>{menu.name}</h3>
                        <p className="ingredients">Текущих блюд: {menu.active_items}</p>
                        <p className="ingredients">
                          В истории удалений: {menu.deleted_items}
                        </p>

                        <div className="meta-row">
                          <span>Обновлено {formatDate(menu.updated_at)}</span>
                          <span>Создано {formatDate(menu.created_at)}</span>
                        </div>

                        <div className="card-actions compact-card-actions">
                          {menu.deleted_at ? (
                            <button
                              type="button"
                              className="btn btn-primary"
                              onClick={() => void handleRestoreMenuCollection(menu)}
                            >
                              Вернуть меню
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => void handleDeleteMenuCollection(menu)}
                            >
                              Архивировать меню
                            </button>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                )
              ) : visibleItems.length === 0 ? (
                <div className="empty-state">
                  {menuView === 'deleted'
                    ? 'Удалённых блюд по текущим фильтрам нет.'
                    : 'По текущим фильтрам ничего не найдено.'}
                </div>
              ) : (
                <div className="card-grid">
                  {visibleItems.map((item) => (
                    <article className="menu-card" key={item.id}>
                      <div className="badge-row">
                        <span className="category-badge">{item.menu_group}</span>
                        <span className="category-badge">{item.section}</span>
                        {item.is_featured ? <span className="accent-badge">Featured</span> : null}
                        <span
                          className={
                            item.is_available
                              ? 'status-badge available'
                              : 'status-badge unavailable'
                          }
                        >
                          {item.is_available ? 'Available' : 'Sold out'}
                        </span>
                        {menuView === 'deleted' ? (
                          <span className="category-badge">
                            {item.deleted_via_menu ? 'Через меню' : 'Вручную'}
                          </span>
                        ) : null}
                      </div>

                      <div className="localized-stack">
                        <div className="localized-line">
                          <span className="locale-mark" aria-hidden="true">
                            🇷🇺
                          </span>
                          <h3>{item.name}</h3>
                        </div>
                        {item.name_en ? (
                          <div className="localized-line secondary-line">
                            <span className="locale-mark" aria-hidden="true">
                              🇬🇧
                            </span>
                            <p className="translation-note">{item.name_en}</p>
                          </div>
                        ) : null}
                      </div>

                      <div className="localized-stack">
                        {item.ingredients ? (
                          <div className="localized-line secondary-line">
                            <span className="locale-mark" aria-hidden="true">
                              🇷🇺
                            </span>
                            <p className="ingredients">{item.ingredients}</p>
                          </div>
                        ) : null}
                        {item.ingredients_en ? (
                          <div className="localized-line secondary-line">
                            <span className="locale-mark" aria-hidden="true">
                              🇬🇧
                            </span>
                            <p className="ingredients translation-note">{item.ingredients_en}</p>
                          </div>
                        ) : null}
                      </div>

                      <div className="variant-strip">{formatVariants(item.variants)}</div>

                      {item.tags.length > 0 ? (
                        <div className="tag-row">
                          {item.tags.map((tag) => (
                            <span className="tiny-pill" key={`${item.id}-${tag}`}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      ) : null}

                      <div className="meta-row">
                        {menuView === 'deleted' && item.deleted_at ? (
                          <span>Удалено {formatDate(item.deleted_at)}</span>
                        ) : (
                          <span>Обновлено {formatDate(item.updated_at)}</span>
                        )}
                        <span>Создано {formatDate(item.created_at)}</span>
                      </div>

                      <div className="card-actions compact-card-actions">
                        {menuView === 'deleted' ? (
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={() => void handleRestoreMenuItem(item)}
                          >
                            Вернуть блюдо
                          </button>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="icon-btn"
                              aria-label={`Редактировать ${item.name}`}
                              title="Редактировать"
                              onClick={() => startEditingMenuItem(item)}
                            >
                              ✏️
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary soldout-btn"
                              onClick={() => void handleAvailabilityToggle(item)}
                            >
                              {item.is_available ? 'Sold out' : 'Вернуть'}
                            </button>
                            <button
                              type="button"
                              className="icon-btn danger"
                              aria-label={`Удалить ${item.name}`}
                              title="Удалить"
                              onClick={() => void handleDeleteMenuItem(item)}
                            >
                              🗑️
                            </button>
                          </>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </main>
          {menuEditorModal}
          {menuCollectionModal}
        </>
      ) : (
        <main className="workspace-grid">
          <section className="board-panel">
            <div className="section-head">
              <div>
                <p className="eyebrow">Кабинет главного администратора</p>
                <h2>Доступ сотрудников</h2>
              </div>
              <span className="count-pill">{users.length} аккаунтов</span>
            </div>

            {usersLoading ? (
              <div className="empty-state">Загрузка сотрудников...</div>
            ) : (
              <div className="user-grid">
                {users.map((user) => (
                  <article className="user-card" key={user.id}>
                    <div className="menu-card-top">
                      <div>
                        <div className="badge-row">
                          <span className="category-badge">{user.role}</span>
                          <span
                            className={
                              user.is_active
                                ? 'status-badge available'
                                : 'status-badge unavailable'
                            }
                          >
                            {user.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </div>
                        <h3>{user.full_name || user.username}</h3>
                      </div>
                    </div>

                    <p className="description">@{user.username}</p>
                    <p className="ingredients">Последний вход: {formatDate(user.last_login_at)}</p>
                    <p className="ingredients">Создан: {formatDate(user.created_at)}</p>

                    <div className="card-actions">
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => startEditingUser(user)}
                      >
                        Редактировать
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => void toggleUserActive(user)}
                      >
                        {user.is_active ? 'Отключить' : 'Включить'}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <aside className="editor-panel">
            <div className="section-head">
              <div>
                <p className="eyebrow">Редактор пользователей</p>
                <h2>{editingUserId === null ? 'Новый сотрудник' : `Пользователь #${editingUserId}`}</h2>
              </div>
            </div>

            <form className="editor-form" onSubmit={handleUserSubmit}>
              <label>
                Username
                <input
                  type="text"
                  value={userForm.username}
                  onChange={(event) =>
                    setUserForm((current) => ({ ...current, username: event.target.value }))
                  }
                  disabled={editingUserId !== null}
                  placeholder="barista_anna"
                />
              </label>

              <label>
                Полное имя
                <input
                  type="text"
                  value={userForm.full_name}
                  onChange={(event) =>
                    setUserForm((current) => ({ ...current, full_name: event.target.value }))
                  }
                  placeholder="Anna Petrova"
                />
              </label>

              <label>
                Роль
                <select
                  value={userForm.role}
                  onChange={(event) =>
                    setUserForm((current) => ({
                      ...current,
                      role: event.target.value as UserFormState['role'],
                    }))
                  }
                >
                  <option value="staff_admin">Сотрудник</option>
                  <option value="super_admin">Главный администратор</option>
                </select>
              </label>

              <label>
                {editingUserId === null ? 'Пароль' : 'Новый пароль (необязательно)'}
                <input
                  type="password"
                  value={userForm.password}
                  onChange={(event) =>
                    setUserForm((current) => ({ ...current, password: event.target.value }))
                  }
                  placeholder="минимум 8 символов"
                />
              </label>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={userForm.is_active}
                  onChange={(event) =>
                    setUserForm((current) => ({
                      ...current,
                      is_active: event.target.checked,
                    }))
                  }
                />
                Доступ к сайту активен
              </label>

              <div className="editor-actions">
                <button type="submit" className="btn btn-primary" disabled={userSaving}>
                  {userSaving
                    ? 'Сохранение...'
                    : editingUserId === null
                      ? 'Создать сотрудника'
                      : 'Сохранить изменения'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={resetUserEditor}>
                  Сбросить
                </button>
              </div>
            </form>
          </aside>
        </main>
      )}
    </div>
  )
}

export default App
