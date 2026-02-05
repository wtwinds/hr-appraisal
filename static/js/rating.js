function setRating(value) {
    document.getElementById("rating").value = value;

    let stars = document.querySelectorAll(".star");

    stars.forEach((star, index) => {
        if (index < value) {
            star.classList.add("text-warning");
        } else {
            star.classList.remove("text-warning");
        }
    });
}
