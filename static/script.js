function addCategoryRow() {
    var tableBody = document.getElementById('categoriesTable').getElementsByTagName('tbody')[0];
    var newRow = tableBody.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    cell1.innerHTML = '<input type="text" name="category_name" class="form-control" placeholder="Category">';
    cell2.innerHTML = '<input type="number" name="category_amount" class="form-control" placeholder="Expected Amount">';
}
