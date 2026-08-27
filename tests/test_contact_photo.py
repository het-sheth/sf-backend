import pytest

BASE = "/api/v1/contacts"
MAX_PHOTO_BYTES = 2 * 1024 * 1024


@pytest.mark.parametrize("mime_type", ["image/jpeg", "image/png", "image/webp"])
def test_create_round_trips_supported_photo(client, payload, photo_data_urls, mime_type):
    photo = photo_data_urls[mime_type]

    response = client.post(BASE, json={**payload, "photo": photo})

    assert response.status_code == 201
    assert response.json()["photo"] == photo


@pytest.mark.parametrize("photo", [pytest.param(None, id="explicit-null")])
def test_create_accepts_null_photo(client, payload, photo):
    response = client.post(BASE, json={**payload, "photo": photo})

    assert response.status_code == 201
    assert response.json()["photo"] is None


def test_create_without_photo_returns_null(client, payload):
    response = client.post(BASE, json=payload)

    assert response.status_code == 201
    assert response.json()["photo"] is None


def test_detail_and_list_include_photo(client, payload, photo_data_urls):
    photo = photo_data_urls["image/png"]
    contact_id = client.post(BASE, json={**payload, "photo": photo}).json()["id"]

    detail = client.get(f"{BASE}/{contact_id}")
    listing = client.get(BASE)

    assert detail.status_code == 200
    assert detail.json()["photo"] == photo
    assert listing.status_code == 200
    assert listing.json()["items"][0]["photo"] == photo


def test_put_with_photo_stores_it(client, payload, photo_data_urls):
    contact_id = client.post(BASE, json=payload).json()["id"]
    photo = photo_data_urls["image/jpeg"]

    response = client.put(f"{BASE}/{contact_id}", json={**payload, "photo": photo})

    assert response.status_code == 200
    assert response.json()["photo"] == photo


def test_put_omitting_photo_clears_it(client, payload, photo_data_urls):
    contact_id = client.post(
        BASE, json={**payload, "photo": photo_data_urls["image/png"]}
    ).json()["id"]

    response = client.put(f"{BASE}/{contact_id}", json=payload)

    assert response.status_code == 200
    assert response.json()["photo"] is None
    assert client.get(f"{BASE}/{contact_id}").json()["photo"] is None


def test_patch_omitting_photo_preserves_it(client, payload, photo_data_urls):
    photo = photo_data_urls["image/webp"]
    contact_id = client.post(BASE, json={**payload, "photo": photo}).json()["id"]

    response = client.patch(f"{BASE}/{contact_id}", json={"job_title": "Programmer"})

    assert response.status_code == 200
    assert response.json()["photo"] == photo
    assert client.get(f"{BASE}/{contact_id}").json()["photo"] == photo


def test_patch_null_clears_photo(client, payload, photo_data_urls):
    contact_id = client.post(
        BASE, json={**payload, "photo": photo_data_urls["image/png"]}
    ).json()["id"]

    response = client.patch(f"{BASE}/{contact_id}", json={"photo": None})

    assert response.status_code == 200
    assert response.json()["photo"] is None
    assert client.get(f"{BASE}/{contact_id}").json()["photo"] is None


def test_patch_valid_photo_replaces_it(client, payload, photo_data_urls):
    contact_id = client.post(
        BASE, json={**payload, "photo": photo_data_urls["image/png"]}
    ).json()["id"]
    replacement = photo_data_urls["image/jpeg"]

    response = client.patch(f"{BASE}/{contact_id}", json={"photo": replacement})

    assert response.status_code == 200
    assert response.json()["photo"] == replacement


@pytest.mark.parametrize(
    "photo",
    [
        pytest.param("https://example.com/photo.png", id="http-url"),
        pytest.param("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==", id="gif"),
        pytest.param("data:image/svg+xml;base64,PHN2Zy8+", id="svg"),
        pytest.param("data:application/pdf;base64,JVBERi0xLjQ=", id="pdf"),
        pytest.param("data:image/bmp;base64,Qk0=", id="unsupported-image-mime"),
        pytest.param("data:image/png;base64", id="malformed-structure"),
        pytest.param("data:image/jpeg;base64,////=", id="malformed-base64"),
        pytest.param("data:image/jpeg;base64,ZE==", id="non-canonical-base64"),
        pytest.param("data:image/png;base64,", id="empty-payload"),
        pytest.param("data:image/webp;base64,UklGRg==", id="short-webp"),
    ],
)
def test_create_rejects_invalid_photo(client, payload, photo):
    response = client.post(BASE, json={**payload, "photo": photo})

    assert response.status_code == 422


def test_create_rejects_mime_signature_mismatch(client, payload, photo_data_urls):
    png_payload = photo_data_urls["image/png"].split(",", 1)[1]
    photo = f"data:image/jpeg;base64,{png_payload}"

    response = client.post(BASE, json={**payload, "photo": photo})

    assert response.status_code == 422


def test_create_accepts_exactly_two_mib(client, payload, sized_png_data_url):
    response = client.post(
        BASE,
        json={**payload, "photo": sized_png_data_url(MAX_PHOTO_BYTES)},
    )

    assert response.status_code == 201


def test_create_rejects_one_byte_over_two_mib(client, payload, sized_png_data_url):
    response = client.post(
        BASE,
        json={**payload, "photo": sized_png_data_url(MAX_PHOTO_BYTES + 1)},
    )

    assert response.status_code == 422


def test_patch_rejects_invalid_photo(client, payload):
    contact_id = client.post(BASE, json=payload).json()["id"]

    response = client.patch(
        f"{BASE}/{contact_id}",
        json={"photo": "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///w=="},
    )

    assert response.status_code == 422
