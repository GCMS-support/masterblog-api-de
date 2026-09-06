'use strict';

window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('post-date').value = new Date().toISOString().slice(0, 10);
    const savedBaseUrl = localStorage.getItem('apiBaseUrl');
    if (savedBaseUrl) {
        document.getElementById('api-base-url').value = savedBaseUrl;
    }
    document.getElementById('search-query').addEventListener('keydown', event => {
        if (event.key === 'Enter') loadPosts();
    });
    loadPosts();
});

function apiBaseUrl() {
    const value = document.getElementById('api-base-url').value.trim().replace(/\/$/, '');
    localStorage.setItem('apiBaseUrl', value);
    return value;
}

async function apiRequest(path, options = {}) {
    const response = await fetch(apiBaseUrl() + path, options);
    let data;
    try {
        data = await response.json();
    } catch (error) {
        throw new Error('Die API hat keine gültige JSON-Antwort geliefert.');
    }
    if (!response.ok) {
        throw new Error(data.error || ('API-Fehler ' + response.status));
    }
    return data;
}

function setStatus(message, isError = false) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.classList.toggle('error', isError);
}

async function loadPosts() {
    const params = new URLSearchParams();
    const search = document.getElementById('search-query').value.trim();
    const sort = document.getElementById('sort-field').value;
    const direction = document.getElementById('sort-direction').value;
    if (search) params.set('search', search);
    if (sort) {
        params.set('sort', sort);
        params.set('direction', direction);
    }

    const query = params.toString();
    setStatus('Beiträge werden geladen …');
    try {
        const posts = await apiRequest('/posts' + (query ? '?' + query : ''));
        renderPosts(posts);
        setStatus(posts.length === 1 ? '1 Beitrag gefunden.' : posts.length + ' Beiträge gefunden.');
    } catch (error) {
        renderPosts([]);
        setStatus(error.message, true);
    }
}

function renderPosts(posts) {
    const container = document.getElementById('post-container');
    container.replaceChildren();
    if (posts.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.textContent = 'Keine Beiträge vorhanden.';
        container.appendChild(empty);
        return;
    }

    posts.forEach(post => {
        const article = document.createElement('article');
        article.className = 'post';

        const title = document.createElement('h2');
        title.textContent = post.title;
        const meta = document.createElement('p');
        meta.className = 'post-meta';
        meta.textContent = (post.author || 'Anonymous') + ' · ' + (post.date || 'Ohne Datum');
        const content = document.createElement('p');
        content.className = 'post-content';
        content.textContent = post.content;
        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'danger';
        deleteButton.textContent = 'Löschen';
        deleteButton.addEventListener('click', () => deletePost(post.id));

        article.append(title, meta, content, deleteButton);
        container.appendChild(article);
    });
}

async function addPost() {
    const title = document.getElementById('post-title').value.trim();
    const content = document.getElementById('post-content').value.trim();
    const author = document.getElementById('post-author').value.trim();
    const date = document.getElementById('post-date').value;
    if (!title || !content) {
        setStatus('Titel und Inhalt sind erforderlich.', true);
        return;
    }

    try {
        await apiRequest('/posts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, content, author, date})
        });
        document.getElementById('post-title').value = '';
        document.getElementById('post-content').value = '';
        document.getElementById('post-author').value = '';
        setStatus('Beitrag wurde gespeichert.');
        await loadPosts();
    } catch (error) {
        setStatus(error.message, true);
    }
}

async function deletePost(postId) {
    try {
        await apiRequest('/posts/' + postId, {method: 'DELETE'});
        setStatus('Beitrag wurde gelöscht.');
        await loadPosts();
    } catch (error) {
        setStatus(error.message, true);
    }
}

function resetFilters() {
    document.getElementById('search-query').value = '';
    document.getElementById('sort-field').value = '';
    document.getElementById('sort-direction').value = 'asc';
    loadPosts();
}
