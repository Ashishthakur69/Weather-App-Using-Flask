document.addEventListener("DOMContentLoaded", function () {
    const themeToggle = document.getElementById("theme-toggle");
    const forecastBtn = document.getElementById("forecast-btn");
    const aboutBtn = document.getElementById("about-btn");
    const weatherBtn = document.getElementById("weather-btn");
    const body = document.body;

    function getPreferredTheme() {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function setTheme(theme, isSystemChange = false) {
        document.documentElement.classList.remove("light-mode", "dark-mode");
        document.documentElement.classList.add(theme);

        if (theme === "dark") {
            body.classList.add("dark-mode");
            body.classList.remove("light-mode");
            themeToggle.innerHTML = "Light Mode ☀️";
        } else {
            body.classList.add("light-mode");
            body.classList.remove("dark-mode");
            themeToggle.innerHTML = "Dark Mode 🌙";
        }

        if (!isSystemChange) {
            localStorage.setItem("theme", theme);
        }
    }

    let savedTheme = localStorage.getItem("theme");
    let systemTheme = getPreferredTheme();
    let currentTheme = savedTheme || systemTheme;
    document.documentElement.classList.add(currentTheme);
    setTheme(currentTheme);

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
        if (!localStorage.getItem("theme")) {
            setTheme(e.matches ? "dark" : "light", true);
        }
    });

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            let newTheme = localStorage.getItem("theme") === "dark" ? "light" : "dark";
            setTheme(newTheme);
        });
    }

    if (forecastBtn) {
        forecastBtn.addEventListener("click", function () {
            const hourlyForecast = document.getElementById("hourly-forecast");
            if (hourlyForecast) {
                hourlyForecast.scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    if (aboutBtn) {
        aboutBtn.addEventListener("click", function () {
            const aboutSection = document.getElementById("about-section");
            if (aboutSection) {
                aboutSection.scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    if (weatherBtn) {
        weatherBtn.addEventListener("click", function () {
            const weatherContainer = document.getElementById("weather-container");
            if (weatherContainer) {
                weatherContainer.scrollIntoView({ behavior: "smooth" });
            }
        });
    }
});

function convertTemperature() {
    let tempElement = document.getElementById("temperature");
    let toggleButton = document.querySelector(".unit-toggle");
    if (!tempElement || !toggleButton) return;
    let currentTemp = tempElement.innerText;
    let value = parseFloat(currentTemp);

    if (isNaN(value)) return;
    if (currentTemp.includes("°C")) {
        tempElement.innerText = (value * 9/5 + 32).toFixed(2) + "°F";
        toggleButton.classList.add("active");
    } else {
        tempElement.innerText = ((value - 32) * 5/9).toFixed(2) + "°C";
        toggleButton.classList.remove("active");
    }
}

function togglePassword(inputId) {
    let passwordField = document.getElementById(inputId);
    let eyeIcon = passwordField.nextElementSibling;

    if (passwordField.type === "password") {
        passwordField.type = "text";
        eyeIcon.textContent = "🙈";
    } else {
        passwordField.type = "password";
        eyeIcon.textContent = "👁️";
    }
}

function getLocation() {
    if (navigator.geolocation) {
        const loading = document.querySelector(".loading");
        loading.style.display = "block";
        navigator.geolocation.getCurrentPosition(
            function (position) {
                let lat = position.coords.latitude;
                let lon = position.coords.longitude;
                $.ajax({
                    url: "/",
                    type: "POST",
                    data: { lat: lat, lon: lon },
                    success: function (response) {
                        updateWeatherDisplay(response);
                        loading.style.display = "none";
                    },
                    error: function () {
                        document.querySelector(".weather-data").innerHTML = "<p>Error fetching weather data.</p>";
                        loading.style.display = "none";
                    }
                });
            },
            function (error) {
                console.error("Geolocation error:", error.message);
                alert(`Geolocation failed: ${error.message}\nPlease enter your city manually.`);
                loading.style.display = "none";
            }
        );
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}

function addCity() {
    let city = document.getElementById("cityInput").value;
    if (city.trim() === "") {
        alert("Please enter a valid city.");
        return;
    }

    $.ajax({
        url: "/add_favorite",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ city: city }),
        success: function (response) {
            if (response.success) {
                let favContainer = document.querySelector(".favorite-cities-list");
                let newCity = document.createElement("span");
                newCity.classList.add("favorite-city");
                newCity.innerHTML = `${city} <span class="remove-city" onclick="removeFavorite('${city}', event)">✖</span>`;
                newCity.setAttribute("onclick", `fetchWeather('${city}')`);
                favContainer.appendChild(newCity);
                document.getElementById("cityInput").value = "";
            } else {
                alert(response.message);
            }
        },
        error: function () {
            alert("Error adding city. Please try again");
        }
    });
}

function removeFavorite(city, event) {
    event.stopPropagation();
    if (confirm(`Remove ${city} from favorites?`)) {
        $.ajax({
            url: `/remove_favorite/${city}`,
            type: "GET",
            success: function () {
                let cityElement = event.target.parentElement;
                cityElement.remove();
                let favList = document.querySelectorAll(".favorite-city");
                if (favList.length === 0) {
                    let favContainer = document.querySelector(".favorite-cities-list");
                    favContainer.innerHTML = '<p class="no-favorites">No favorite cities added yet.</p>';
                }
            },
            error: function () {
                alert("Error removing city. Please try again.");
            }
        });
    }
}

function fetchWeather(city) {
    if (!city || city.trim() === "") {
        document.querySelector(".weather-data").innerHTML = "<p>Please enter a valid city name.</p>";
        return;
    }
    const loading = document.querySelector(".loading");
    loading.style.display = "block";
    $.ajax({
        url: "/",
        type: "POST",
        data: { city: city },
        success: function (response) {
            updateWeatherDisplay(response);
            localStorage.setItem("lastCity", city);
            loading.style.display = "none";
        },
        error: function () {
            document.querySelector(".weather-data").innerHTML = "<p>Error fetching weather data. Please try again.</p>";
            loading.style.display = "none";
        }
    });
}

function updateWeatherDisplay(response) {
    let weatherData = document.querySelector(".weather-data");
    let hourlyForecast = document.querySelector("#hourly-forecast .carousel-inner");
    let fiveDayForecast = document.querySelector("#five-day-forecast .forecast-table tbody");

    // Update current weather
    if (response.data && 'weather_desc' in response.data) {
        weatherData.innerHTML = `
            <div>
                <h3>${response.data.cityname}</h3>
                <div class="weather-icon">
                    ${getWeatherIcon(response.data.weather_desc)}
                </div>
                <h4 id="temperature">${response.data.temp_cel}°C</h4>
                <button class="btn btn-secondary unit-toggle" onclick="convertTemperature()">Convert °C/°F</button>
                <p>${response.data.weather_desc}</p>
                <p><strong>Humidity:</strong> ${response.data.humidity}%</p>
                <p><strong>Pressure:</strong> ${response.data.pressure_hpa} hPa</p>
                <p><strong>Wind Speed:</strong> ${response.data.wind_speed_mps} m/s / ${response.data.wind_speed_mph} mph</p>
                <p><strong>Visibility:</strong> ${response.data.visibility} km</p>
                <p><strong>Sunrise:</strong> ${response.data.sunrise}</p>
                <p><strong>Sunset:</strong> ${response.data.sunset}</p>
                <div class="additional-info">
                    <p><strong>Country Code:</strong> ${response.data.country_code}</p>
                    <p><strong>Coordinates:</strong> ${response.data.coordinate}</p>
                </div>
            </div>
        `;
    } else {
        weatherData.innerHTML = "<p>Error fetching weather data. Please try again.</p>";
    }

    // Update hourly forecast
    if (response.hourly_forecast && response.hourly_forecast.length > 0) {
        hourlyForecast.innerHTML = ""; // Clear existing items
        response.hourly_forecast.forEach((hour, index) => {
            let isActive = index === 0 ? "active" : ""; // Make first item active for carousel
            hourlyForecast.innerHTML += `
                <div class="carousel-item ${isActive}">
                    <div class="weather-container p-3">
                        <h4>${hour.time}</h4>
                        <p class="temp-highlight">${hour.temp_cel}°C / ${hour.temp_fah}°F</p>
                        <p>${hour.weather}</p>
                    </div>
                </div>
            `;
        });
    } else {
        hourlyForecast.innerHTML = "<p>No hourly forecast data available.</p>";
    }

    // Update 5-day forecast
    if (response.forecast && response.forecast.length > 0) {
        fiveDayForecast.innerHTML = ""; // Clear existing rows
        response.forecast.forEach(day => {
            let weatherIcon = getWeatherIcon(day.weather);
            fiveDayForecast.innerHTML += `
                <tr>
                    <td>${day.date}</td>
                    <td class="temp-highlight">${day.temp_cel}°C</td>
                    <td>${weatherIcon} ${day.weather}</td>
                </tr>
            `;
        });
    } else {
        fiveDayForecast.innerHTML = "<tr><td colspan='3'>No 5-day forecast data available.</td></tr>";
    }
}

function getWeatherIcon(weatherDesc) {
    weatherDesc = weatherDesc.toLowerCase();
    if (weatherDesc.includes("clear")) return "☀️";
    if (weatherDesc.includes("cloud")) return "☁️";
    if (weatherDesc.includes("rain")) return "🌧️";
    if (weatherDesc.includes("storm")) return "⛈️";
    if (weatherDesc.includes("snow")) return "❄️";
    if (weatherDesc.includes("mist")) return "🌫️";
    return "🌡️";
}
if (aboutBtn) {
    aboutBtn.addEventListener("click", function () {
        const aboutSection = document.getElementById("about-section");
        if (aboutSection) {
            aboutSection.scrollIntoView({ behavior: "smooth" });
        }
    });
}