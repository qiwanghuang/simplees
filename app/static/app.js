// 页面状态。keyword 为空时走数据库分页接口，不为空时走 ES 搜索接口。
const state = {
  page: 1,
  size: 10,
  total: 0,
  keyword: "",
  items: [],
};

const content = document.getElementById("content");
const summary = document.getElementById("summary");
const pageInfo = document.getElementById("pageInfo");
const notice = document.getElementById("notice");
const keywordInput = document.getElementById("keywordInput");
const searchButton = document.getElementById("searchButton");
const resetButton = document.getElementById("resetButton");
const prevButton = document.getElementById("prevButton");
const nextButton = document.getElementById("nextButton");
const editDialog = document.getElementById("editDialog");
const editForm = document.getElementById("editForm");
const closeDialogButton = document.getElementById("closeDialogButton");
const cancelEditButton = document.getElementById("cancelEditButton");
const editProductId = document.getElementById("editProductId");
const editName = document.getElementById("editName");
const editDescription = document.getElementById("editDescription");
const editPrice = document.getElementById("editPrice");
const editStatus = document.getElementById("editStatus");
const editBrandId = document.getElementById("editBrandId");
const editCategoryId = document.getElementById("editCategoryId");

function buildApiUrl() {
  const params = new URLSearchParams({
    page: String(state.page),
    size: String(state.size),
  });

  if (state.keyword) {
    params.set("q", state.keyword);
    return `/api/products/search?${params.toString()}`;
  }

  return `/api/products?${params.toString()}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPrice(price) {
  if (price === null || price === undefined) {
    return "-";
  }

  return `¥${Number(price).toFixed(2)}`;
}

function showNotice(message, type = "success") {
  notice.textContent = message;
  notice.className = `notice ${type}`;
  notice.hidden = false;

  window.setTimeout(() => {
    notice.hidden = true;
  }, 2600);
}

function findProduct(productId) {
  return state.items.find((item) => item.id === productId);
}

function renderTable(items) {
  if (items.length === 0) {
    content.innerHTML = '<div class="empty">暂无商品数据</div>';
    return;
  }

  const rows = items.map((item) => `
    <tr>
      <td class="id">${escapeHtml(item.id)}</td>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.brand.name)}</td>
      <td>${escapeHtml(item.category.name)}</td>
      <td>${formatPrice(item.price)}</td>
      <td><span class="status ${item.status === "inactive" ? "inactive" : ""}">${escapeHtml(item.status)}</span></td>
      <td>
        <div class="actions">
          <button class="text" data-action="edit" data-id="${escapeHtml(item.id)}">编辑</button>
          <button class="text danger-text" data-action="delete" data-id="${escapeHtml(item.id)}">删除</button>
        </div>
      </td>
    </tr>
  `).join("");

  content.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>商品 ID</th>
          <th>商品名称</th>
          <th>品牌</th>
          <th>类目</th>
          <th>价格</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(state.total / state.size));

  pageInfo.textContent = `第 ${state.page} 页 / 共 ${totalPages} 页`;
  prevButton.disabled = state.page <= 1;
  nextButton.disabled = state.page >= totalPages;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    let message = `接口请求失败：${response.status}`;

    try {
      const error = await response.json();
      message = error.detail || message;
    } catch {
      // 响应不是 JSON 时使用默认错误。
    }

    throw new Error(message);
  }

  return response.json();
}

async function loadProducts() {
  summary.textContent = "正在加载商品数据";
  content.innerHTML = '<div class="empty">加载中...</div>';

  try {
    const data = await requestJson(buildApiUrl());

    state.total = data.total;
    state.items = data.items;
    renderTable(data.items);
    renderPagination();

    const modeText = state.keyword ? `搜索：${state.keyword}` : "全部商品";
    summary.textContent = `${modeText}，共 ${data.total} 条`;
  } catch (error) {
    content.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
    summary.textContent = "加载失败";
  }
}

function openEditDialog(product) {
  editProductId.value = product.id;
  editName.value = product.name;
  editDescription.value = product.description || "";
  editPrice.value = product.price ?? "";
  editStatus.value = product.status;
  editBrandId.value = product.brand.id;
  editCategoryId.value = product.category.id;
  editDialog.showModal();
}

async function saveProduct() {
  const productId = editProductId.value;
  const payload = {
    name: editName.value.trim(),
    description: editDescription.value.trim() || null,
    price: editPrice.value === "" ? null : editPrice.value,
    brand_id: editBrandId.value.trim(),
    category_id: editCategoryId.value.trim(),
    status: editStatus.value,
  };

  await requestJson(`/api/products/${encodeURIComponent(productId)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  editDialog.close();
  showNotice("商品修改成功，ES 将通过 Canal 异步同步");
  await loadProducts();
}

async function deleteProduct(productId) {
  const product = findProduct(productId);
  const productName = product ? product.name : productId;

  if (!window.confirm(`确认删除商品：${productName}？`)) {
    return;
  }

  await requestJson(`/api/products/${encodeURIComponent(productId)}`, {
    method: "DELETE",
  });

  showNotice("商品删除成功，ES 将通过 Canal 异步同步");

  if (state.items.length === 1 && state.page > 1) {
    state.page -= 1;
  }

  await loadProducts();
}

searchButton.addEventListener("click", () => {
  state.keyword = keywordInput.value.trim();
  state.page = 1;
  loadProducts();
});

resetButton.addEventListener("click", () => {
  state.keyword = "";
  state.page = 1;
  keywordInput.value = "";
  loadProducts();
});

keywordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    searchButton.click();
  }
});

prevButton.addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadProducts();
  }
});

nextButton.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(state.total / state.size));

  if (state.page < totalPages) {
    state.page += 1;
    loadProducts();
  }
});

content.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");

  if (!button) {
    return;
  }

  const productId = button.dataset.id;
  const action = button.dataset.action;

  try {
    if (action === "edit") {
      const product = findProduct(productId);

      if (product) {
        openEditDialog(product);
      }
    }

    if (action === "delete") {
      await deleteProduct(productId);
    }
  } catch (error) {
    showNotice(error.message, "error");
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await saveProduct();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

closeDialogButton.addEventListener("click", () => {
  editDialog.close();
});

cancelEditButton.addEventListener("click", () => {
  editDialog.close();
});

loadProducts();
